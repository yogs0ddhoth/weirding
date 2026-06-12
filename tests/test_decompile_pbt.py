"""Property-based round-trip tests for dump_xml (reverse edge B -> A).

Property: for any acyclic, union-free IR in the genuinely-supported subset,
    weirding.compile(dump_xml(ir)) == ir

The strategy builds IR *directly* in the exact canonical form weirding.compile
emits, so equality can be asserted EXACTLY (per the Phase 2 round-trip note: do
not weaken the assertion to paper over an asymmetry — instead constrain the
strategy to the supported subset).

Subset boundaries and why (each keeps the round trip exact):
  * minimum/maximum are floats — compile stores them via float(); str(float)
    re-parses to the identical float, so any generated float round-trips.
  * default is a string — compile stores default via str() unchanged.
  * enum members are stringified and re-coerced by compile per the field type;
    we generate members that survive str() -> coerce (ints, plain floats, and
    pipe-free / whitespace-trimmed strings).
  * No unions besides the nullable pattern; no $ref/$defs; no const/format.
"""

from __future__ import annotations

import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import weirding
from weirding._decompile import dump_xml

pytestmark = pytest.mark.pbt

# Tag names safe end-to-end through the pipeline (see test_schema_pbt rationale).
_TAG_NAME = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,11}", fullmatch=True)
_SCALAR_TYPE = st.sampled_from(["string", "integer", "number", "boolean"])

# enum string members: no '|' (the join delimiter) and no surrounding whitespace
# that lxml attribute normalization would alter. Letters/digits/spaces, trimmed.
_ENUM_STR = (
    st.text(
        alphabet=string.ascii_letters + string.digits + " ",
        min_size=1,
        max_size=8,
    )
    .map(str.strip)
    .filter(lambda s: bool(s))
)


@st.composite
def _scalar_schema(draw: st.DrawFn) -> dict:
    """Build a scalar leaf schema in canonical compile() form."""
    type_ = draw(_SCALAR_TYPE)
    schema: dict = {"type": type_}

    # Optional same-named string attrs.
    if draw(st.booleans()):
        schema["description"] = draw(_ENUM_STR)
    if type_ == "string" and draw(st.booleans()):
        schema["minLength"] = draw(st.integers(min_value=0, max_value=20))
    if type_ == "string" and draw(st.booleans()):
        schema["maxLength"] = draw(st.integers(min_value=0, max_value=20))
    if type_ in ("integer", "number") and draw(st.booleans()):
        # floats, matching compile()'s float() coercion of minimum/maximum.
        schema["minimum"] = draw(
            st.floats(
                min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False
            )
        )
    if type_ in ("integer", "number") and draw(st.booleans()):
        schema["maximum"] = draw(
            st.floats(
                min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False
            )
        )
    # enum, type-coerced exactly as compile() would.
    if draw(st.booleans()):
        if type_ == "integer":
            members = draw(
                st.lists(
                    st.integers(min_value=-1000, max_value=1000), min_size=1, max_size=4
                )
            )
        elif type_ == "number":
            members = draw(
                st.lists(
                    st.floats(
                        min_value=-1000,
                        max_value=1000,
                        allow_nan=False,
                        allow_infinity=False,
                    ),
                    min_size=1,
                    max_size=4,
                )
            )
        else:
            # string and boolean enums alike are stored as the raw string list.
            members = draw(st.lists(_ENUM_STR, min_size=1, max_size=4))
        schema["enum"] = members
    return schema


@st.composite
def _array_schema(draw: st.DrawFn, item_strategy: st.SearchStrategy) -> dict:
    """Build an array schema with an explicit x-weirding-item-tag."""
    schema: dict = {
        "type": "array",
        "items": draw(item_strategy),
        "x-weirding-item-tag": draw(_TAG_NAME),
    }
    if draw(st.booleans()):
        schema["minItems"] = draw(st.integers(min_value=0, max_value=10))
    if draw(st.booleans()):
        schema["maxItems"] = draw(st.integers(min_value=0, max_value=10))
    return schema


def _object_schema(properties_strategy: st.SearchStrategy) -> st.SearchStrategy:
    """Build a (nested) object schema with a unique-keyed property map."""

    @st.composite
    def build(draw: st.DrawFn) -> dict:
        props = draw(properties_strategy)
        required = [name for name in props if draw(st.booleans())]
        return {"type": "object", "properties": props, "required": required}

    return build()


def _value_schema() -> st.SearchStrategy:
    """Recursive schema strategy: scalars, arrays, and nested objects."""

    def extend(children: st.SearchStrategy) -> st.SearchStrategy:
        props = st.dictionaries(_TAG_NAME, children, min_size=1, max_size=4)
        return st.one_of(
            _array_schema(children),
            _object_schema(props),
        )

    return st.recursive(_scalar_schema(), extend, max_leaves=6)


@st.composite
def _root_ir(draw: st.DrawFn) -> dict:
    """Build a canonical root IR: type=object, title, properties, required."""
    title = draw(_TAG_NAME)
    props = draw(st.dictionaries(_TAG_NAME, _value_schema(), min_size=1, max_size=4))
    required = [name for name in props if draw(st.booleans())]
    return {
        "type": "object",
        "title": title,
        "properties": props,
        "required": required,
    }


@given(_root_ir())
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_compile_dump_xml_round_trip(ir: dict) -> None:
    """compile(dump_xml(ir)) reproduces the canonical IR exactly."""
    xml = dump_xml(ir)
    assert weirding.compile(xml) == ir
