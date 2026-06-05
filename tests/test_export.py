"""Tests for weirding.to_json_schema (the provider-ready schema exporter)."""

from __future__ import annotations

import copy

import pytest

import weirding
from weirding import SchemaError


def _all_dicts(node):
    """Yield every dict node in a schema document, depth-first."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _all_dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_dicts(item)


def _all_keys(node):
    """Yield every dict key appearing anywhere in a schema document."""
    for d in _all_dicts(node):
        yield from d.keys()


# ---------------------------------------------------------------------------
# strict=False
# ---------------------------------------------------------------------------


def test_non_strict_strips_x_weirding_keys():
    ir = weirding.compile(
        """
        <Response>
          <tags type="array">
            <tag type="string"/>
          </tags>
        </Response>
        """
    )
    assert any(k.startswith("x-weirding-") for k in _all_keys(ir))

    out = weirding.to_json_schema(ir, strict=False)
    assert not any(k.startswith("x-weirding-") for k in _all_keys(out))


def test_non_strict_preserves_standard_keywords():
    ir = {
        "type": "object",
        "title": "Doc",
        "description": "A document.",
        "properties": {
            "name": {
                "type": "string",
                "pattern": "^[A-Z]",
                "minLength": 1,
                "description": "the name",
            },
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "color": {"type": "string", "enum": ["red", "green"]},
        },
        "required": ["name"],
    }
    out = weirding.to_json_schema(ir, strict=False)

    name = out["properties"]["name"]
    assert name["pattern"] == "^[A-Z]"
    assert name["minLength"] == 1
    assert name["description"] == "the name"
    assert out["properties"]["score"]["minimum"] == 0
    assert out["properties"]["score"]["maximum"] == 100
    assert out["properties"]["color"]["enum"] == ["red", "green"]
    assert out["description"] == "A document."


def test_non_strict_does_not_mutate_input():
    ir = weirding.compile(
        '<Response><tags type="array"><tag type="string"/></tags></Response>'
    )
    original = copy.deepcopy(ir)
    weirding.to_json_schema(ir, strict=False)
    assert ir == original


# ---------------------------------------------------------------------------
# strict=True — core shape
# ---------------------------------------------------------------------------


def test_strict_sets_additional_properties_false_on_every_object():
    ir = weirding.compile(
        """
        <Response>
          <name type="string"/>
          <address type="object">
            <city type="string"/>
          </address>
        </Response>
        """
    )
    out = weirding.to_json_schema(ir, strict=True)
    for node in _all_dicts(out):
        if node.get("type") == "object" or "properties" in node:
            assert node["additionalProperties"] is False


def test_strict_promotes_all_properties_to_required():
    ir = weirding.compile(
        """
        <Response>
          <name type="string" required="true"/>
          <nickname type="string" required="false"/>
        </Response>
        """
    )
    # In the IR, nickname is optional.
    assert ir["required"] == ["name"]

    out = weirding.to_json_schema(ir, strict=True)
    assert set(out["required"]) == {"name", "nickname"}


def test_strict_collapses_nullable_anyof_to_type_array():
    ir = weirding.compile('<Response><note type="string" nullable="true"/></Response>')
    note_ir = ir["properties"]["note"]
    assert "anyOf" in note_ir  # weirding emits the null-union form

    out = weirding.to_json_schema(ir, strict=True)
    note = out["properties"]["note"]
    assert note["type"] == ["string", "null"]
    assert "anyOf" not in note


def test_strict_has_no_banned_constructs_anywhere():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {
            "name": {
                "type": "string",
                "pattern": "^[A-Z]",
                "minLength": 1,
                "format": "email",
                "default": "x",
            },
            "score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "multipleOf": 2,
            },
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "x-weirding-item-tag": "tag",
            },
        },
        "required": ["name"],
    }
    out = weirding.to_json_schema(ir, strict=True)

    banned = {
        "anyOf",
        "oneOf",
        "allOf",
        "pattern",
        "prefixItems",
        "$ref",
        "$defs",
        "format",
        "minimum",
        "maximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "uniqueItems",
        "default",
        "patternProperties",
        "propertyNames",
        "minProperties",
        "maxProperties",
    }
    present = set(_all_keys(out))
    assert banned.isdisjoint(present), banned & present
    assert not any(k.startswith("x-weirding-") for k in present)


def test_strict_does_not_mutate_input():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "name": {"type": "string", "pattern": "x"},
        },
        "required": ["name"],
    }
    original = copy.deepcopy(ir)
    weirding.to_json_schema(ir, strict=True)
    assert ir == original


# ---------------------------------------------------------------------------
# strict=True — $ref / $defs inlining
# ---------------------------------------------------------------------------


def test_strict_inlines_local_ref_and_drops_defs():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {
            "addr": {"$ref": "#/$defs/Address"},
        },
        "required": ["addr"],
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"city": {"type": "string", "minLength": 1}},
                "required": ["city"],
            }
        },
    }
    out = weirding.to_json_schema(ir, strict=True)
    assert "$defs" not in out
    assert "$ref" not in set(_all_keys(out))

    addr = out["properties"]["addr"]
    assert addr["type"] == "object"
    assert addr["additionalProperties"] is False
    assert addr["required"] == ["city"]
    # stripped keyword from the inlined def is gone
    assert "minLength" not in addr["properties"]["city"]


def test_strict_inlines_nullable_ref():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {
            "addr": {"anyOf": [{"$ref": "#/$defs/Address"}, {"type": "null"}]},
        },
        "required": ["addr"],
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            }
        },
    }
    out = weirding.to_json_schema(ir, strict=True)
    addr = out["properties"]["addr"]
    assert addr["type"] == ["object", "null"]
    assert addr["additionalProperties"] is False


def test_strict_unresolvable_ref_raises():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"addr": {"$ref": "#/$defs/Missing"}},
        "required": ["addr"],
        "$defs": {},
    }
    with pytest.raises(SchemaError, match="Missing"):
        weirding.to_json_schema(ir, strict=True)


def test_strict_non_local_ref_raises():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"addr": {"$ref": "https://example.com/Address"}},
        "required": ["addr"],
    }
    with pytest.raises(SchemaError, match="local"):
        weirding.to_json_schema(ir, strict=True)


# ---------------------------------------------------------------------------
# strict=True — error cases
# ---------------------------------------------------------------------------


def test_strict_non_null_anyof_raises():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {
            "val": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "required": ["val"],
    }
    with pytest.raises(SchemaError, match="anyOf"):
        weirding.to_json_schema(ir, strict=True)


def test_strict_oneof_raises():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"val": {"oneOf": [{"type": "string"}]}},
        "required": ["val"],
    }
    with pytest.raises(SchemaError, match="oneOf"):
        weirding.to_json_schema(ir, strict=True)


def test_strict_null_wrapped_root_raises():
    ir = {"anyOf": [{"type": "object", "properties": {}}, {"type": "null"}]}
    with pytest.raises(SchemaError, match="nullable root"):
        weirding.to_json_schema(ir, strict=True)


def test_strict_exceeding_64_keys_raises():
    # Build a wide object whose strict transform crosses the 64-key cap.
    props = {f"f{i}": {"type": "string"} for i in range(40)}
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": props,
        "required": list(props),
    }
    with pytest.raises(SchemaError, match="64"):
        weirding.to_json_schema(ir, strict=True)


def test_strict_small_schema_under_limit_succeeds():
    ir = weirding.compile(
        '<Response><name type="string"/><score type="integer"/></Response>'
    )
    out = weirding.to_json_schema(ir, strict=True)
    assert out["additionalProperties"] is False
    assert set(out["required"]) == {"name", "score"}
