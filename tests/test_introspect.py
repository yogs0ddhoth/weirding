"""Unit tests for weirding._introspect.to_schema (reverse edge C -> B)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

import weirding
from weirding._exceptions import SchemaError
from weirding._introspect import to_schema

# ---------------------------------------------------------------------------
# 1. Scalar-only model
# ---------------------------------------------------------------------------


def test_scalar_only_model() -> None:
    class Person(BaseModel):
        name: str
        age: int

    ir = to_schema(Person)
    assert ir["type"] == "object"
    assert ir["properties"]["name"]["type"] == "string"
    assert ir["properties"]["age"]["type"] == "integer"
    assert set(ir["required"]) == {"name", "age"}
    # The model is never mutated, and no array keys are synthesized for scalars.
    assert "x-weirding-item-tag" not in str(ir)


# ---------------------------------------------------------------------------
# 2. Nested-object model — $defs / $ref left intact
# ---------------------------------------------------------------------------


def test_nested_object_model_keeps_refs() -> None:
    class Address(BaseModel):
        street: str

    class Order(BaseModel):
        address: Address

    ir = to_schema(Order)
    # Pydantic hoists nested models into $defs/$ref; to_schema leaves them intact.
    assert "$defs" in ir
    assert "$ref" in ir["properties"]["address"]


# ---------------------------------------------------------------------------
# 3. weirding-built array model preserves x-weirding-item-tag
# ---------------------------------------------------------------------------


def test_weirding_built_array_preserves_item_tag() -> None:
    source_ir = {
        "type": "object",
        "title": "Response",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "x-weirding-item-tag": "tag",
            }
        },
        "required": ["tags"],
    }
    model = weirding.from_schema(source_ir, name="Response")

    ir = to_schema(model)
    assert ir["properties"]["tags"]["x-weirding-item-tag"] == "tag"


# ---------------------------------------------------------------------------
# 4. Hand-written list field lacking item-tag gets the fallback tag
# ---------------------------------------------------------------------------


def test_hand_written_list_gets_fallback_tag() -> None:
    class Bag(BaseModel):
        tags: list[str]
        category: str

    ir = to_schema(Bag)
    # "tags" -> singularized "tag" via the shared fallback.
    assert ir["properties"]["tags"]["x-weirding-item-tag"] == "tag"


def test_hand_written_list_no_trailing_s_gets_item() -> None:
    class Bag(BaseModel):
        data: list[str]

    ir = to_schema(Bag)
    # "data" has no trailing "s" to strip -> literal "item".
    assert ir["properties"]["data"]["x-weirding-item-tag"] == "item"


# ---------------------------------------------------------------------------
# 5. Tuple field -> prefixItems -> SchemaError
# ---------------------------------------------------------------------------


def test_tuple_field_raises_schema_error() -> None:
    class HasTuple(BaseModel):
        pair: tuple[int, str]

    with pytest.raises(SchemaError) as exc_info:
        to_schema(HasTuple)
    message = str(exc_info.value)
    assert "prefixItems" in message
    # The error names the offending path so the field is locatable.
    assert "pair" in message


# ---------------------------------------------------------------------------
# 6. min/max collapse guard — type-correct keywords survive
# ---------------------------------------------------------------------------


def test_array_min_max_items_preserved() -> None:
    """An array field's minItems/maxItems must survive as array-typed keywords.

    Guards against json-schema-to-pydantic collapsing array bounds onto the
    wrong keyword (e.g. minLength) on a dependency bump.
    """
    source_ir = {
        "type": "object",
        "title": "Response",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "x-weirding-item-tag": "tag",
                "minItems": 1,
                "maxItems": 3,
            }
        },
        "required": ["tags"],
    }
    model = weirding.from_schema(source_ir, name="Response")

    ir = to_schema(model)
    tags = ir["properties"]["tags"]
    assert tags["minItems"] == 1
    assert tags["maxItems"] == 3
    # Must NOT collapse onto string-typed keywords.
    assert "minLength" not in tags
    assert "maxLength" not in tags


def test_string_min_max_length_preserved() -> None:
    """A string field's minLength/maxLength must survive as string-typed keywords."""
    source_ir = {
        "type": "object",
        "title": "Response",
        "properties": {
            "code": {
                "type": "string",
                "minLength": 2,
                "maxLength": 5,
            }
        },
        "required": ["code"],
    }
    model = weirding.from_schema(source_ir, name="Response")

    ir = to_schema(model)
    code = ir["properties"]["code"]
    assert code["minLength"] == 2
    assert code["maxLength"] == 5
    # Must NOT collapse onto array-typed keywords.
    assert "minItems" not in code
    assert "maxItems" not in code
