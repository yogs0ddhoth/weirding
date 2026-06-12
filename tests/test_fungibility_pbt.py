"""Full-hexagon property-based test: the closed XML <-> IR <-> Pydantic loop.

Walks every edge of the triangle from a single authored XML schema (ADR-0012):

    xml --compile--> ir1 --from_schema--> model --to_schema--> ir2
    ir1 --dump_xml--> xml2 --compile--> ir3

Canonical equality is asserted ONLY at the two genuinely-canonical, fully-inlined
points produced by ``compile``:

    * ir3 == ir1   (dump_xml then re-compile reproduces the canonical IR exactly)

The ``to_schema`` midpoint (ir2) is NOT asserted equal to the inlined IR raw:
Pydantic unconditionally hoists nested models into ``$defs`` / ``$ref`` and injects
additive ``title`` / ``default`` keys. So ir2 is compared modulo $ref-inlining and
that additive noise (see the negative consequences of ADR-0012).

Run with: pytest tests/test_fungibility_pbt.py
Fast-iteration: pytest -k "not pbt"  (excludes this file via marker)
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import weirding

pytestmark = pytest.mark.pbt  # allows: pytest -k "not pbt"

# ---------------------------------------------------------------------------
# Strategies — author XML schemas with scalars, arrays, and nested objects
# ---------------------------------------------------------------------------

# Letter-start NCNames safe end-to-end through json-schema-to-pydantic (mirrors
# the rationale in test_schema_pbt.py / test_introspect_pbt.py).
_TAG_NAME = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,11}", fullmatch=True)
_SCALAR_TYPE = st.sampled_from(["string", "integer", "number", "boolean"])


def _attrs(type_: str, required: bool) -> str:
    """Render the attribute string for a leaf/array element."""
    out = f'type="{type_}"'
    if not required:
        out += ' required="false"'
    return out


@st.composite
def _scalar_field(draw: st.DrawFn, tag: str) -> str:
    """A self-closing scalar field element."""
    type_ = draw(_SCALAR_TYPE)
    required = draw(st.booleans())
    return f"<{tag} {_attrs(type_, required)}/>"


@st.composite
def _array_field(draw: st.DrawFn, tag: str) -> str:
    """An array element with a single scalar item-template child."""
    required = draw(st.booleans())
    item_tag = draw(_TAG_NAME)
    item_type = draw(_SCALAR_TYPE)
    open_attrs = 'type="array"'
    if not required:
        open_attrs += ' required="false"'
    item = f'<{item_tag} type="{item_type}"/>'
    return f"<{tag} {open_attrs}>{item}</{tag}>"


@st.composite
def _object_field(draw: st.DrawFn, tag: str) -> str:
    """A nested object element with 1-3 scalar children."""
    required = draw(st.booleans())
    n = draw(st.integers(min_value=1, max_value=3))
    child_tags = draw(st.lists(_TAG_NAME, min_size=n, max_size=n, unique=True))
    children = "".join(draw(_scalar_field(t)) for t in child_tags)
    open_attrs = "" if required else ' required="false"'
    return f"<{tag}{open_attrs}>{children}</{tag}>"


@st.composite
def _field(draw: st.DrawFn, tag: str) -> str:
    """A field that is a scalar, array, or nested object."""
    kind = draw(st.sampled_from(["scalar", "array", "object"]))
    if kind == "scalar":
        return draw(_scalar_field(tag))
    if kind == "array":
        return draw(_array_field(tag))
    return draw(_object_field(tag))


@st.composite
def _schema_xml(draw: st.DrawFn) -> str:
    """Draw an annotation XML schema mixing scalars, arrays, and nested objects.

    At least one field is forced to be a nested object so the $ref trap on the
    to_schema midpoint is exercised.
    """
    root = draw(_TAG_NAME)
    n = draw(st.integers(min_value=1, max_value=4))
    tags = draw(st.lists(_TAG_NAME, min_size=n + 1, max_size=n + 1, unique=True))
    # Force the first field to be a nested object; vary the rest.
    parts = [draw(_object_field(tags[0]))]
    for tag in tags[1:]:
        parts.append(draw(_field(tag)))
    inner = "".join(parts)
    return f"<{root}>{inner}</{root}>"


# ---------------------------------------------------------------------------
# Comparison helpers — inline $defs/$ref and strip additive noise on the
# to_schema midpoint (it is $ref-bearing and title/default-noisy).
# ---------------------------------------------------------------------------

_ADDITIVE_KEYS = frozenset({"title", "default"})


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    """Recursively inline local ``#/$defs/NAME`` references against *defs*."""
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            name = ref.rsplit("/", 1)[-1]
            target = _inline_refs(copy.deepcopy(defs[name]), defs)
            for key, value in node.items():
                if key != "$ref":
                    target.setdefault(key, _inline_refs(value, defs))
            return target
        return {key: _inline_refs(value, defs) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def _strip_additive(node: Any) -> Any:
    """Recursively drop additive ``title`` / ``default`` keys."""
    if isinstance(node, dict):
        return {
            key: _strip_additive(value)
            for key, value in node.items()
            if key not in _ADDITIVE_KEYS
        }
    if isinstance(node, list):
        return [_strip_additive(item) for item in node]
    return node


def _normalize(ir: dict[str, Any]) -> dict[str, Any]:
    """Inline refs, drop $defs, and strip additive noise for comparison."""
    document = copy.deepcopy(ir)
    defs = document.pop("$defs", None)
    if isinstance(defs, dict):
        document = _inline_refs(document, defs)
    return _strip_additive(document)


# ---------------------------------------------------------------------------
# The full-hexagon property
# ---------------------------------------------------------------------------


@given(_schema_xml())
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_full_hexagon_round_trip(xml: str) -> None:
    """Every edge of the XML <-> IR <-> Pydantic loop is consistent.

    Canonical equality is asserted only at the two ``compile`` outputs (ir1, ir3,
    both fully inlined). The ``to_schema`` midpoint ir2 is compared modulo
    $ref-inlining + title/default noise, never raw — Pydantic hoists nested models
    into $defs/$ref.
    """
    ir1 = weirding.compile(xml)
    model = weirding.from_schema(ir1, name="Model")
    ir2 = weirding.to_schema(model)
    xml2 = weirding.dump_xml(ir1)
    ir3 = weirding.compile(xml2)

    # Genuinely-canonical, inlined: assert exact equality.
    assert ir3 == ir1

    # to_schema midpoint: $ref-bearing + title/default noise -> compare modulo both.
    assert _normalize(ir2) == _normalize(ir1)
