"""Tests for build_model() — JSON Schema IR → Pydantic v2 BaseModel."""

import pytest
from pydantic import BaseModel, ValidationError

from weirding._models import build_model

# ---------------------------------------------------------------------------
# 1. Flat object schema → BaseModel subclass with correct fields
# ---------------------------------------------------------------------------


def test_flat_schema_produces_correct_fields() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name", "age"],
    }
    Model = build_model(schema)
    assert set(Model.model_fields.keys()) == {"name", "age"}
    instance = Model.model_validate({"name": "Alice", "age": 30})
    assert instance.name == "Alice"  # type: ignore[attr-defined]
    assert instance.age == 30  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 2. Nested object → nested BaseModel
# ---------------------------------------------------------------------------


def test_nested_object_produces_nested_model() -> None:
    schema = {
        "type": "object",
        "properties": {
            "address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                },
                "required": ["street", "city"],
            }
        },
        "required": ["address"],
    }
    Model = build_model(schema)
    address_annotation = Model.model_fields["address"].annotation
    assert issubclass(address_annotation, BaseModel)  # type: ignore[arg-type]
    instance = Model.model_validate(
        {"address": {"street": "Main St", "city": "Springfield"}}
    )
    assert instance.address.street == "Main St"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 3. Array field → list-typed field
# ---------------------------------------------------------------------------


def test_array_field_is_list_typed() -> None:
    schema = {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["tags"],
    }
    Model = build_model(schema)
    instance = Model.model_validate({"tags": ["a", "b", "c"]})
    assert instance.tags == ["a", "b", "c"]  # type: ignore[attr-defined]
    # Pydantic should reject a non-list value
    with pytest.raises(ValidationError):
        Model.model_validate({"tags": "not-a-list"})


# ---------------------------------------------------------------------------
# 4. Optional field → field has default None / is not required
# ---------------------------------------------------------------------------


def test_optional_field_defaults_to_none() -> None:
    schema = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "string"},
        },
        "required": ["required_field"],
    }
    Model = build_model(schema)
    # optional_field must be present but not required
    assert "optional_field" in Model.model_fields
    assert not Model.model_fields["optional_field"].is_required()
    instance = Model.model_validate({"required_field": "yes"})
    assert instance.optional_field is None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 5. Enum field → Literal or enum type
# ---------------------------------------------------------------------------


def test_enum_field_constrains_values() -> None:
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
        },
        "required": ["status"],
    }
    Model = build_model(schema)
    instance = Model.model_validate({"status": "active"})
    assert instance.status == "active"  # type: ignore[attr-defined]
    # Values outside the enum must be rejected
    with pytest.raises(ValidationError):
        Model.model_validate({"status": "unknown"})


# ---------------------------------------------------------------------------
# 6. additionalProperties: false → extra fields raise ValidationError
# ---------------------------------------------------------------------------


def test_additional_properties_false_rejects_extra_fields() -> None:
    schema = {
        "type": "object",
        "properties": {
            "f": {"type": "string"},
        },
        "required": ["f"],
        "additionalProperties": False,
    }
    Model = build_model(schema)
    # Known field must still work
    instance = Model.model_validate({"f": "hello"})
    assert instance.f == "hello"  # type: ignore[attr-defined]
    # Extra field must be rejected — this is the evidence signal
    with pytest.raises(ValidationError):
        Model.model_validate({"f": "hello", "unexpected": "extra"})


# ---------------------------------------------------------------------------
# 7. Schema without additionalProperties: false → extra fields NOT rejected
# ---------------------------------------------------------------------------


def test_no_additional_properties_flag_allows_extra_fields() -> None:
    schema = {
        "type": "object",
        "properties": {
            "f": {"type": "string"},
        },
        "required": ["f"],
    }
    Model = build_model(schema)
    # Must not raise — extra fields are silently ignored
    instance = Model.model_validate({"f": "hello", "extra": "ok"})
    assert instance.f == "hello"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 8. build_model() returns a BaseModel subclass
# ---------------------------------------------------------------------------


def test_result_is_basemodel_subclass() -> None:
    schema = {
        "type": "object",
        "properties": {"x": {"type": "integer"}},
        "required": ["x"],
    }
    Model = build_model(schema)
    assert issubclass(Model, BaseModel)


# ---------------------------------------------------------------------------
# 9. name parameter sets the model class __name__
# ---------------------------------------------------------------------------


def test_name_parameter_sets_class_name() -> None:
    schema = {
        "type": "object",
        "properties": {"val": {"type": "string"}},
        "required": ["val"],
    }
    Model = build_model(schema, name="MyCustomModel")
    assert Model.__name__ == "MyCustomModel"


def test_default_name_is_model() -> None:
    schema = {
        "type": "object",
        "properties": {"val": {"type": "string"}},
        "required": ["val"],
    }
    Model = build_model(schema)
    assert Model.__name__ == "Model"


# ---------------------------------------------------------------------------
# 10. Top-level description → generated class __doc__ (ADR-0011)
# ---------------------------------------------------------------------------


def test_top_level_description_propagates_to_doc() -> None:
    description = "A response from the assistant with a name and a score."
    schema = {
        "type": "object",
        "description": description,
        "properties": {
            "name": {"type": "string"},
            "score": {"type": "integer"},
        },
        "required": ["name", "score"],
    }
    Model = build_model(schema)
    assert Model.__doc__ == description
    assert Model.model_json_schema()["description"] == description


def test_no_description_leaves_doc_none() -> None:
    schema = {
        "type": "object",
        "properties": {"val": {"type": "string"}},
        "required": ["val"],
    }
    Model = build_model(schema)
    assert Model.__doc__ is None


# ---------------------------------------------------------------------------
# 11. Regression guard: extra="forbid" survives description propagation
# ---------------------------------------------------------------------------


def test_extra_forbid_still_enforced_with_description() -> None:
    description = "A strict object that forbids unexpected fields."
    schema = {
        "type": "object",
        "description": description,
        "properties": {"f": {"type": "string"}},
        "required": ["f"],
        "additionalProperties": False,
    }
    Model = build_model(schema)
    # Description propagation holds.
    assert Model.__doc__ == description
    # extra="forbid" behavior holds simultaneously.
    instance = Model.model_validate({"f": "hello"})
    assert instance.f == "hello"  # type: ignore[attr-defined]
    with pytest.raises(ValidationError):
        Model.model_validate({"f": "hello", "unexpected": "extra"})
