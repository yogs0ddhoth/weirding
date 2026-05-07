"""Tests for compile_schema() — JSON Schema IR compiler."""

import pytest

from weirding._exceptions import ParseError, UnsupportedDialectError
from weirding._schema import compile_schema

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def schema_with_field(inner_xml: str) -> str:
    """Wrap a single field element inside a root <Response> element."""
    return f"<Response>{inner_xml}</Response>"


# ---------------------------------------------------------------------------
# 1. Scalar string field (default type)
# ---------------------------------------------------------------------------


def test_scalar_string_default_type() -> None:
    xml = schema_with_field("<name />")
    ir = compile_schema(xml)
    assert ir["properties"]["name"] == {"type": "string"}


# ---------------------------------------------------------------------------
# 2. Scalar integer field (explicit type="integer")
# ---------------------------------------------------------------------------


def test_scalar_integer_explicit_type() -> None:
    xml = schema_with_field('<count type="integer" />')
    ir = compile_schema(xml)
    assert ir["properties"]["count"] == {"type": "integer"}


# ---------------------------------------------------------------------------
# 3. Object inferred from children (no type attribute)
# ---------------------------------------------------------------------------


def test_object_inferred_from_children() -> None:
    xml = schema_with_field("<address><street /><city /></address>")
    ir = compile_schema(xml)
    addr = ir["properties"]["address"]
    assert addr["type"] == "object"
    assert "street" in addr["properties"]
    assert "city" in addr["properties"]
    assert addr["properties"]["street"] == {"type": "string"}


# ---------------------------------------------------------------------------
# 4. Array field with named child → items + x-weirding-item-tag
# ---------------------------------------------------------------------------


def test_array_with_child_element() -> None:
    xml = schema_with_field('<items type="array"><item /></items>')
    ir = compile_schema(xml)
    items_schema = ir["properties"]["items"]
    assert items_schema["type"] == "array"
    assert items_schema["items"] == {"type": "string"}
    assert items_schema["x-weirding-item-tag"] == "item"


# ---------------------------------------------------------------------------
# 5. Optional field (required="false") → absent from required[]
# ---------------------------------------------------------------------------


def test_optional_field_not_in_required() -> None:
    xml = schema_with_field('<nickname required="false" />')
    ir = compile_schema(xml)
    assert "nickname" not in ir["required"]


# ---------------------------------------------------------------------------
# 6. Required field (default) → present in required[]
# ---------------------------------------------------------------------------


def test_required_field_in_required_by_default() -> None:
    xml = schema_with_field("<username />")
    ir = compile_schema(xml)
    assert "username" in ir["required"]


def test_required_field_explicit_true() -> None:
    xml = schema_with_field('<username required="true" />')
    ir = compile_schema(xml)
    assert "username" in ir["required"]


# ---------------------------------------------------------------------------
# 7. Enum attribute pipe-split → list
# ---------------------------------------------------------------------------


def test_enum_pipe_split() -> None:
    xml = schema_with_field('<color enum="red|green|blue" />')
    ir = compile_schema(xml)
    assert ir["properties"]["color"]["enum"] == ["red", "green", "blue"]


# ---------------------------------------------------------------------------
# 8. nullable="true" → anyOf shape
# ---------------------------------------------------------------------------


def test_nullable_scalar() -> None:
    xml = schema_with_field('<score type="number" nullable="true" />')
    ir = compile_schema(xml)
    schema = ir["properties"]["score"]
    assert "anyOf" in schema
    assert {"type": "number"} in schema["anyOf"]
    assert {"type": "null"} in schema["anyOf"]
    assert len(schema["anyOf"]) == 2


def test_nullable_object() -> None:
    xml = schema_with_field('<meta nullable="true"><key /><value /></meta>')
    ir = compile_schema(xml)
    schema = ir["properties"]["meta"]
    assert "anyOf" in schema
    branch = schema["anyOf"][0]
    assert branch["type"] == "object"
    assert "key" in branch["properties"]
    assert {"type": "null"} == schema["anyOf"][1]


# ---------------------------------------------------------------------------
# 9. pattern attribute → pattern key in schema
# ---------------------------------------------------------------------------


def test_pattern_attribute() -> None:
    xml = schema_with_field('<code pattern="^[A-Z]{3}$" />')
    ir = compile_schema(xml)
    assert ir["properties"]["code"]["pattern"] == "^[A-Z]{3}$"


# ---------------------------------------------------------------------------
# 10. minimum / maximum → numeric values
# ---------------------------------------------------------------------------


def test_minimum_maximum() -> None:
    xml = schema_with_field('<age type="integer" minimum="0" maximum="150" />')
    ir = compile_schema(xml)
    field = ir["properties"]["age"]
    assert field["minimum"] == 0.0
    assert field["maximum"] == 150.0


def test_minimum_float() -> None:
    xml = schema_with_field('<ratio type="number" minimum="0.5" maximum="1.0" />')
    ir = compile_schema(xml)
    field = ir["properties"]["ratio"]
    assert field["minimum"] == 0.5
    assert field["maximum"] == 1.0


# ---------------------------------------------------------------------------
# 11. XSD root element → UnsupportedDialectError
# ---------------------------------------------------------------------------


def test_xsd_root_raises_unsupported_dialect() -> None:
    xsd_xml = (
        '<?xml version="1.0"?>'
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        "</xs:schema>"
    )
    with pytest.raises(UnsupportedDialectError, match="weirding\\[xsd\\]"):
        compile_schema(xsd_xml)


# ---------------------------------------------------------------------------
# 12. Malformed XML → ParseError
# ---------------------------------------------------------------------------


def test_malformed_xml_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        compile_schema("<unclosed>")


def test_empty_string_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        compile_schema("")


def test_empty_bytes_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        compile_schema(b"")


# ---------------------------------------------------------------------------
# 13. Nested object (object with object child) → correct nesting
# ---------------------------------------------------------------------------


def test_nested_object() -> None:
    xml = '<Order><customer><name /><age type="integer" /></customer></Order>'
    ir = compile_schema(xml)
    assert ir["title"] == "Order"
    customer = ir["properties"]["customer"]
    assert customer["type"] == "object"
    assert customer["properties"]["name"] == {"type": "string"}
    assert customer["properties"]["age"] == {"type": "integer"}
    assert "name" in customer["required"]
    assert "age" in customer["required"]


# ---------------------------------------------------------------------------
# 14. Description attribute → description key in schema
# ---------------------------------------------------------------------------


def test_description_attribute() -> None:
    xml = schema_with_field('<bio description="A short biography" />')
    ir = compile_schema(xml)
    assert ir["properties"]["bio"]["description"] == "A short biography"


# ---------------------------------------------------------------------------
# Top-level IR shape
# ---------------------------------------------------------------------------


def test_top_level_shape() -> None:
    xml = "<Person><name /><age type='integer' /></Person>"
    ir = compile_schema(xml)
    assert ir["type"] == "object"
    assert ir["title"] == "Person"
    assert "properties" in ir
    assert "required" in ir
    assert isinstance(ir["required"], list)


# ---------------------------------------------------------------------------
# Array with no child → items={"type": "string"}, no x-weirding-item-tag
# ---------------------------------------------------------------------------


def test_array_no_child_element() -> None:
    xml = schema_with_field('<tags type="array" />')
    ir = compile_schema(xml)
    field = ir["properties"]["tags"]
    assert field["type"] == "array"
    assert field["items"] == {"type": "string"}
    assert "x-weirding-item-tag" not in field


# ---------------------------------------------------------------------------
# bytes input
# ---------------------------------------------------------------------------


def test_bytes_input() -> None:
    xml = b"<Root><field /></Root>"
    ir = compile_schema(xml)
    assert ir["title"] == "Root"
    assert "field" in ir["properties"]


# ---------------------------------------------------------------------------
# min/max on string → minLength/maxLength
# ---------------------------------------------------------------------------


def test_min_max_on_string() -> None:
    xml = schema_with_field('<username min="3" max="32" />')
    ir = compile_schema(xml)
    field = ir["properties"]["username"]
    assert field["minLength"] == 3
    assert field["maxLength"] == 32


# ---------------------------------------------------------------------------
# min/max on array → minItems/maxItems
# ---------------------------------------------------------------------------


def test_min_max_on_array() -> None:
    xml = schema_with_field('<tags type="array" min="1" max="10"><tag /></tags>')
    ir = compile_schema(xml)
    field = ir["properties"]["tags"]
    assert field["minItems"] == 1
    assert field["maxItems"] == 10


# ---------------------------------------------------------------------------
# default attribute
# ---------------------------------------------------------------------------


def test_default_attribute() -> None:
    xml = schema_with_field('<status default="pending" />')
    ir = compile_schema(xml)
    assert ir["properties"]["status"]["default"] == "pending"
