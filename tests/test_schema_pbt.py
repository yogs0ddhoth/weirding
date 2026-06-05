"""Property-based tests for weirding schema compilation and round-trip identity.

Run with: pytest tests/test_schema_pbt.py
Fast-iteration: pytest -k "not pbt"  (excludes this file via marker)
"""

import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import weirding

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Legal XML NCNames that the weirding pipeline handles end-to-end.
# Must start with a letter (not underscore) to avoid the json-schema-to-pydantic
# limitation where underscore-only names (e.g. "_") are mangled to empty-string
# field names by pydantic's alias stripping.  All-letter-start names are safe.
# Bounded to 20 chars to keep generated XML small.
_TAG_NAME = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,19}", fullmatch=True)

_SCALAR_TYPE = st.sampled_from(["string", "integer", "number", "boolean"])


@st.composite
def _field_element(draw: st.DrawFn) -> str:
    """Draw a single weirding-annotated scalar field element as an XML string."""
    tag = draw(_TAG_NAME)
    type_ = draw(_SCALAR_TYPE)
    required = draw(st.booleans())
    attrs = f'type="{type_}"'
    if not required:
        attrs += ' required="false"'
    return f"<{tag} {attrs}/>"


@st.composite
def flat_schema_xml(draw: st.DrawFn) -> str:
    """Draw a flat weirding-annotation XML schema (no nesting, 1-6 fields)."""
    root = draw(_TAG_NAME)
    n = draw(st.integers(min_value=1, max_value=6))
    # Ensure unique field tag names within the schema
    tags = draw(st.lists(_TAG_NAME, min_size=n, max_size=n, unique=True))
    type_ = draw(st.lists(_SCALAR_TYPE, min_size=n, max_size=n))
    required_flags = draw(st.lists(st.booleans(), min_size=n, max_size=n))
    fields = []
    for tag, t, req in zip(tags, type_, required_flags):
        attrs = f'type="{t}"'
        if not req:
            attrs += ' required="false"'
        fields.append(f"  <{tag} {attrs}/>")
    inner = "\n".join(fields)
    return f"<{root}>\n{inner}\n</{root}>"


# Safe string alphabet for XML text content: letters, digits, spaces.
# Excludes XML metacharacters (< > & " ').
_SAFE_TEXT = st.text(
    alphabet=string.ascii_letters + string.digits + " ",
    max_size=20,
)


@st.composite
def schema_and_valid_data(draw: st.DrawFn) -> tuple[str, str]:
    """Draw (schema_xml, data_xml) where data is always valid per the schema."""
    root = draw(_TAG_NAME)
    n = draw(st.integers(min_value=1, max_value=4))
    tags = draw(st.lists(_TAG_NAME, min_size=n, max_size=n, unique=True))
    types = draw(st.lists(_SCALAR_TYPE, min_size=n, max_size=n))

    schema_fields = []
    data_elements = []

    for tag, type_ in zip(tags, types):
        schema_fields.append(f'  <{tag} type="{type_}"/>')

        if type_ == "string":
            value = draw(_SAFE_TEXT)
        elif type_ == "integer":
            value = str(draw(st.integers(min_value=0, max_value=10000)))
        elif type_ == "number":
            value = str(
                draw(
                    st.floats(
                        min_value=0,
                        max_value=10000,
                        allow_nan=False,
                        allow_infinity=False,
                    )
                )
            )
        else:  # boolean
            value = "true" if draw(st.booleans()) else "false"

        data_elements.append(f"  <{tag}>{value}</{tag}>")

    schema_xml = f"<{root}>\n" + "\n".join(schema_fields) + f"\n</{root}>"
    data_xml = f"<{root}>\n" + "\n".join(data_elements) + f"\n</{root}>"
    return schema_xml, data_xml


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.pbt  # allows: pytest -k "not pbt"


@given(flat_schema_xml())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_ir_well_formedness(schema_xml: str) -> None:
    """IR from any valid annotation schema must satisfy structural invariants.

    Verifies: type==object, title present, properties dict, required list,
    and the prefixItems prohibition (MEMORY.md rule 11).
    """
    ir = weirding.compile(schema_xml)
    assert ir.get("type") == "object"
    assert "title" in ir
    assert isinstance(ir.get("properties"), dict)
    assert isinstance(ir.get("required"), list)
    assert "prefixItems" not in str(ir)


@given(schema_and_valid_data())
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_round_trip_identity(schema_and_data: tuple[str, str]) -> None:
    """parse(to_xml(instance), Model) must equal the original instance.

    Verifies: serialization and deserialization are symmetric for all scalar
    field types weirding supports.
    """
    schema_xml, data_xml = schema_and_data
    Model = weirding.define_model(schema_xml)
    instance = weirding.parse(data_xml, Model)
    roundtripped = weirding.parse(weirding.to_xml(instance), Model)
    assert instance.model_dump() == roundtripped.model_dump()
