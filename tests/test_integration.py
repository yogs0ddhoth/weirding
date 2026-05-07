"""Integration tests for the weirding public API.

All imports come from the top-level `weirding` package — the public surface.
These tests exercise the full pipeline: compile → from_schema / define_model →
parse → to_xml → round-trip.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from weirding import (
    DTOBuilder,
    ParseError,
    UnsupportedDialectError,
    compile,
    define_model,
    from_schema,
    parse,
    to_xml,
)

# ---------------------------------------------------------------------------
# Shared schema XML used across multiple tests
# ---------------------------------------------------------------------------

_FLAT_SCHEMA_XML = (
    '<response><title type="string"/><score type="number" required="false"/></response>'
)

# ---------------------------------------------------------------------------
# 1. compile() returns a JSON Schema dict
# ---------------------------------------------------------------------------


def test_compile_returns_json_schema_dict() -> None:
    result = compile(_FLAT_SCHEMA_XML)

    assert result["type"] == "object"
    assert result["title"] == "response"
    assert "title" in result["properties"]
    assert "score" in result["properties"]
    # "score" is optional → must not appear in required
    assert "title" in result["required"]
    assert "score" not in result["required"]


# ---------------------------------------------------------------------------
# 2. from_schema() default path (Pydantic)
# ---------------------------------------------------------------------------


def test_from_schema_default_pydantic_builder() -> None:
    schema = compile(_FLAT_SCHEMA_XML)
    model = from_schema(schema, name="Response")

    assert issubclass(model, BaseModel)
    assert model.__name__ == "Response"
    assert "title" in model.model_fields
    assert "score" in model.model_fields


# ---------------------------------------------------------------------------
# 3. define_model() shortcut — name derived from root tag
# ---------------------------------------------------------------------------


def test_define_model_name_from_root_tag() -> None:
    model = define_model(_FLAT_SCHEMA_XML)

    # Root tag is "response" — _sanitize_name leaves it as-is
    assert model.__name__ == "response"
    assert issubclass(model, BaseModel)
    assert "title" in model.model_fields
    assert "score" in model.model_fields


def test_define_model_equivalent_to_two_step() -> None:
    """define_model() and compile()+from_schema() must produce the same fields."""
    schema = compile(_FLAT_SCHEMA_XML)
    model_two_step = from_schema(schema, name="response")
    model_shortcut = define_model(_FLAT_SCHEMA_XML)

    two_step_fields = set(model_two_step.model_fields.keys())
    shortcut_fields = set(model_shortcut.model_fields.keys())
    assert two_step_fields == shortcut_fields


# ---------------------------------------------------------------------------
# 4. parse() basic
# ---------------------------------------------------------------------------


def test_parse_flat_model() -> None:
    model = define_model(_FLAT_SCHEMA_XML)
    data_xml = "<response><title>Hello</title><score>9.5</score></response>"

    instance = parse(data_xml, model)

    assert instance.title == "Hello"  # type: ignore[attr-defined]
    # Pydantic coerces the string "9.5" to float for a number field
    assert instance.score == 9.5 or instance.score == "9.5"  # type: ignore[attr-defined]


def test_parse_optional_field_absent() -> None:
    """score is optional — omitting it should not raise."""
    model = define_model(_FLAT_SCHEMA_XML)
    data_xml = "<response><title>Only Title</title></response>"

    instance = parse(data_xml, model)

    assert instance.title == "Only Title"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 5. to_xml() basic
# ---------------------------------------------------------------------------


def test_to_xml_basic() -> None:
    model = define_model(_FLAT_SCHEMA_XML)
    data_xml = "<response><title>Hello</title><score>9.5</score></response>"
    instance = parse(data_xml, model)

    xml_out = to_xml(instance)

    assert "<title>Hello</title>" in xml_out
    # Root tag comes from the model class name
    assert "<response>" in xml_out or xml_out.startswith("<response")


# ---------------------------------------------------------------------------
# 6. Full round-trip
# ---------------------------------------------------------------------------


def test_round_trip_flat_model() -> None:
    schema_xml = '<person><name type="string"/><age type="integer"/></person>'
    model = define_model(schema_xml)
    data_xml = "<person><name>Alice</name><age>30</age></person>"

    first = parse(data_xml, model)
    xml_out = to_xml(first)
    second = parse(xml_out, model)

    assert second == first


def test_round_trip_nested_model() -> None:
    schema_xml = '<order><customer><name/><age type="integer"/></customer></order>'
    model = define_model(schema_xml)
    data_xml = "<order><customer><name>Bob</name><age>42</age></customer></order>"

    first = parse(data_xml, model)
    xml_out = to_xml(first)
    second = parse(xml_out, model)

    assert second == first


def test_round_trip_array_field() -> None:
    schema_xml = "<results><items type='array'><item type='string'/></items></results>"
    model = define_model(schema_xml)
    data_xml = (
        "<results><items><item>a</item><item>b</item><item>c</item></items></results>"
    )

    first = parse(data_xml, model)
    xml_out = to_xml(first)
    second = parse(xml_out, model)

    assert second == first
    assert second.items == ["a", "b", "c"]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 7. from_schema() with custom DTOBuilder
# ---------------------------------------------------------------------------


class CustomBuilder:
    """Minimal DTOBuilder that always returns the built-in dict type."""

    def build(self, schema: dict, *, name: str) -> type:
        return dict


def test_custom_builder_satisfies_protocol() -> None:
    assert isinstance(CustomBuilder(), DTOBuilder)


def test_from_schema_with_custom_builder() -> None:
    schema = compile(_FLAT_SCHEMA_XML)
    result = from_schema(schema, builder=CustomBuilder())
    assert result is dict


# ---------------------------------------------------------------------------
# 8. Error paths
# ---------------------------------------------------------------------------


def test_parse_malformed_xml_raises_parse_error() -> None:
    model = define_model(_FLAT_SCHEMA_XML)
    with pytest.raises(ParseError):
        parse("<unclosed", model)


def test_compile_xsd_raises_unsupported_dialect_error() -> None:
    xsd_xml = (
        '<?xml version="1.0"?>'
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        "</xs:schema>"
    )
    with pytest.raises(UnsupportedDialectError):
        compile(xsd_xml)


def test_compile_empty_xml_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        compile("")


def test_compile_empty_bytes_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        compile(b"")


# ---------------------------------------------------------------------------
# 9. Array round-trip (dedicated)
# ---------------------------------------------------------------------------


def test_array_round_trip() -> None:
    schema_xml = "<results><items type='array'><item type='string'/></items></results>"
    data_xml = "<results><items><item>a</item><item>b</item></items></results>"
    model = define_model(schema_xml)

    first = parse(data_xml, model)
    xml_out = to_xml(first)
    second = parse(xml_out, model)

    assert second.items == first.items  # type: ignore[attr-defined]
    assert list(second.items) == ["a", "b"]  # type: ignore[attr-defined]
