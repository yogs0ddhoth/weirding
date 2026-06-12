"""Property-based tests for weirding._introspect.to_schema (reverse edge C -> B).

Round-trip property (ADR-0012): ``to_schema(from_schema(ir)) ~= ir``, where
``~=`` means equality AFTER inlining the ``$defs`` / ``$ref`` that Pydantic
hoists nested models into, and modulo the additive ``title`` and ``default``
keys Pydantic injects. Exact dict equality is explicitly NOT asserted — see the
negative consequences of ADR-0012.

Run with: pytest tests/test_introspect_pbt.py
Fast-iteration: pytest -k "not pbt"  (excludes this file via marker)
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import weirding
from weirding._introspect import to_schema

pytestmark = pytest.mark.pbt  # allows: pytest -k "not pbt"

# ---------------------------------------------------------------------------
# Strategies — canonical, fully-inlined IR (the shape compile() emits)
# ---------------------------------------------------------------------------

# Field names safe for the json-schema-to-pydantic pipeline (letter-start, no
# leading underscore — mirrors the constraint in test_schema_pbt.py).
_FIELD_NAME = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,15}", fullmatch=True)

_SCALAR_TYPE = st.sampled_from(["string", "integer", "number", "boolean"])


def _object_ir(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


@st.composite
def _scalar_field(draw: st.DrawFn) -> dict[str, Any]:
    return {"type": draw(_SCALAR_TYPE)}


@st.composite
def _flat_ir(draw: st.DrawFn) -> dict[str, Any]:
    """Draw a flat object IR: 1-5 scalar fields, some optional."""
    names = draw(st.lists(_FIELD_NAME, min_size=1, max_size=5, unique=True))
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name in names:
        properties[name] = draw(_scalar_field())
        if draw(st.booleans()):
            required.append(name)
    ir = _object_ir(properties, required)
    ir["title"] = draw(_FIELD_NAME)
    return ir


@st.composite
def _nested_ir(draw: st.DrawFn) -> dict[str, Any]:
    """Draw an object IR with at least one nested object field plus scalars."""
    scalar_names = draw(st.lists(_FIELD_NAME, min_size=1, max_size=3, unique=True))
    nested_name = draw(_FIELD_NAME.filter(lambda n: n not in scalar_names))

    properties: dict[str, Any] = {}
    required: list[str] = []
    for name in scalar_names:
        properties[name] = draw(_scalar_field())
        if draw(st.booleans()):
            required.append(name)

    inner_names = draw(st.lists(_FIELD_NAME, min_size=1, max_size=3, unique=True))
    inner_props: dict[str, Any] = {}
    inner_required: list[str] = []
    for iname in inner_names:
        inner_props[iname] = draw(_scalar_field())
        if draw(st.booleans()):
            inner_required.append(iname)
    properties[nested_name] = _object_ir(inner_props, inner_required)
    # Make the nested field required so it is not wrapped/optionalized away.
    required.append(nested_name)

    ir = _object_ir(properties, required)
    ir["title"] = draw(_FIELD_NAME)
    return ir


# ---------------------------------------------------------------------------
# Comparison helpers — inline $defs/$ref and strip additive noise
# ---------------------------------------------------------------------------

_ADDITIVE_KEYS = frozenset({"title", "default"})


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    """Recursively inline local ``#/$defs/NAME`` references against *defs*."""
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            name = ref.rsplit("/", 1)[-1]
            target = _inline_refs(copy.deepcopy(defs[name]), defs)
            # Merge any sibling keywords (Pydantic rarely emits these on a $ref).
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
# Properties
# ---------------------------------------------------------------------------


@given(_flat_ir())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_flat_round_trip_modulo_noise(ir: dict[str, Any]) -> None:
    """to_schema(from_schema(ir)) == ir for flat IR, modulo title/default."""
    model = weirding.from_schema(ir, name="Model")
    out = to_schema(model)
    assert _normalize(out) == _normalize(ir)


@given(_nested_ir())
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_nested_round_trip_modulo_refs_and_noise(ir: dict[str, Any]) -> None:
    """to_schema(from_schema(ir)) == ir for nested IR, after inlining $defs/$ref.

    Pydantic hoists nested models into $defs/$ref, so the to_schema output is
    $ref-bearing. The comparison inlines those refs before asserting equality.
    """
    model = weirding.from_schema(ir, name="Model")
    out = to_schema(model)
    assert "$defs" in out  # confirm the $ref trap actually fired
    assert _normalize(out) == _normalize(ir)
