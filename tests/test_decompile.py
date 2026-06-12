"""Unit tests for weirding._decompile.dump_xml (reverse edge B -> A).

dump_xml is the structural inverse of weirding.compile. These tests verify the
emitter for every construct, the round trip compile(dump_xml(ir)) == ir for
canonical inlined IR, the drop/reject decisions for out-of-vocabulary keywords,
and that failure-mode messages are dump_xml-appropriate (never "strict mode").
"""

from __future__ import annotations

import copy

import pytest
from lxml import etree

import weirding
from weirding import SchemaError
from weirding._decompile import dump_xml


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode())


# ---------------------------------------------------------------------------
# Round trip: canonical IR survives compile(dump_xml(ir)) == ir
# ---------------------------------------------------------------------------


def test_flat_scalars_round_trip():
    ir = weirding.compile(
        """
        <Response>
          <name type="string"/>
          <score type="integer"/>
          <ratio type="number"/>
          <ok type="boolean"/>
        </Response>
        """
    )
    assert weirding.compile(dump_xml(ir)) == ir


def test_required_and_optional():
    ir = weirding.compile(
        """
        <Response>
          <name type="string" required="true"/>
          <nickname type="string" required="false"/>
        </Response>
        """
    )
    # Sanity: nickname optional in the IR.
    assert ir["required"] == ["name"]

    xml = dump_xml(ir)
    root = _parse(xml)
    by_tag = {child.tag: child for child in root}
    # required default is omitted; only the optional field is annotated.
    assert by_tag["name"].get("required") is None
    assert by_tag["nickname"].get("required") == "false"

    assert weirding.compile(xml) == ir


def test_constraints_min_max_pattern_enum():
    ir = weirding.compile(
        """
        <Response>
          <name type="string" min="1" max="10" pattern="^[A-Z]"/>
          <color type="string" enum="red|green|blue"/>
        </Response>
        """
    )
    xml = dump_xml(ir)
    root = _parse(xml)
    by_tag = {child.tag: child for child in root}
    assert by_tag["name"].get("min") == "1"
    assert by_tag["name"].get("max") == "10"
    assert by_tag["name"].get("pattern") == "^[A-Z]"
    assert by_tag["color"].get("enum") == "red|green|blue"

    assert weirding.compile(xml) == ir


def test_constraints_minimum_maximum_default():
    ir = weirding.compile(
        """
        <Response>
          <score type="integer" minimum="0" maximum="100"/>
          <label type="string" default="none"/>
        </Response>
        """
    )
    xml = dump_xml(ir)
    # Round trip is the binding assertion: minimum/maximum are floats in the IR
    # and compile re-applies float(), so str(float) round-trips exactly.
    assert weirding.compile(xml) == ir


def test_integer_enum_round_trips():
    ir = weirding.compile('<Response><n type="integer" enum="1|2|3"/></Response>')
    assert ir["properties"]["n"]["enum"] == [1, 2, 3]
    assert weirding.compile(dump_xml(ir)) == ir


def test_nullable_anyof_shape():
    ir = weirding.compile('<Response><note type="string" nullable="true"/></Response>')
    # weirding emits the anyOf null-union form.
    assert "anyOf" in ir["properties"]["note"]

    xml = dump_xml(ir)
    root = _parse(xml)
    note = next(c for c in root if c.tag == "note")
    assert note.get("nullable") == "true"
    assert note.get("type") == "string"

    assert weirding.compile(xml) == ir


def test_nullable_type_array_shape():
    # The shape to_json_schema(strict=True) and some foreign IR emit.
    ir = {
        "type": "object",
        "title": "Response",
        "properties": {"note": {"type": ["string", "null"]}},
        "required": ["note"],
    }
    xml = dump_xml(ir)
    root = _parse(xml)
    note = next(c for c in root if c.tag == "note")
    assert note.get("nullable") == "true"
    assert note.get("type") == "string"

    # Re-compiling yields the canonical anyOf shape (both express the same thing).
    recompiled = weirding.compile(xml)
    assert recompiled["properties"]["note"] == {
        "anyOf": [{"type": "string"}, {"type": "null"}]
    }


def test_array_explicit_item_tag():
    ir = weirding.compile(
        """
        <Response>
          <tags type="array"><tag type="string"/></tags>
        </Response>
        """
    )
    assert ir["properties"]["tags"]["x-weirding-item-tag"] == "tag"

    xml = dump_xml(ir)
    root = _parse(xml)
    tags = next(c for c in root if c.tag == "tags")
    children = list(tags)
    assert len(children) == 1
    assert children[0].tag == "tag"

    assert weirding.compile(xml) == ir


def test_array_fallback_item_tag():
    # IR with no x-weirding-item-tag -> emitter uses the literal "item" tag.
    ir = {
        "type": "object",
        "title": "Response",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["tags"],
    }
    xml = dump_xml(ir)
    root = _parse(xml)
    tags = next(c for c in root if c.tag == "tags")
    assert [c.tag for c in tags] == ["item"]


def test_array_with_minitems_maxitems():
    ir = weirding.compile(
        """
        <Response>
          <tags type="array" min="1" max="5"><tag type="string"/></tags>
        </Response>
        """
    )
    assert ir["properties"]["tags"]["minItems"] == 1
    assert ir["properties"]["tags"]["maxItems"] == 5

    xml = dump_xml(ir)
    root = _parse(xml)
    tags = next(c for c in root if c.tag == "tags")
    assert tags.get("min") == "1"
    assert tags.get("max") == "5"

    assert weirding.compile(xml) == ir


def test_nested_object():
    ir = weirding.compile(
        """
        <Response>
          <addr type="object">
            <city type="string"/>
            <zip type="string" required="false"/>
          </addr>
        </Response>
        """
    )
    xml = dump_xml(ir)
    root = _parse(xml)
    addr = next(c for c in root if c.tag == "addr")
    assert addr.get("type") == "object"
    assert {c.tag for c in addr} == {"city", "zip"}

    assert weirding.compile(xml) == ir


def test_local_ref_inlining():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"addr": {"$ref": "#/$defs/Address"}},
        "required": ["addr"],
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            }
        },
    }
    xml = dump_xml(ir)
    root = _parse(xml)
    addr = next(c for c in root if c.tag == "addr")
    assert addr.get("type") == "object"
    assert [c.tag for c in addr] == ["city"]
    assert "$ref" not in xml and "$defs" not in xml

    # The inlined output round-trips to the inlined IR.
    expected = {
        "type": "object",
        "title": "Doc",
        "properties": {
            "addr": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            }
        },
        "required": ["addr"],
    }
    assert weirding.compile(xml) == expected


def test_root_level_ref():
    ir = {
        "$ref": "#/$defs/Root",
        "$defs": {
            "Root": {
                "type": "object",
                "title": "Doc",
                "properties": {"a": {"type": "string"}},
                "required": ["a"],
            }
        },
    }
    xml = dump_xml(ir)
    root = _parse(xml)
    # Root element name comes from the resolved schema's title.
    assert root.tag == "Doc"
    assert [c.tag for c in root] == ["a"]


def test_root_title_fallback_to_model():
    ir = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    root = _parse(dump_xml(ir))
    assert root.tag == "Model"


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def test_does_not_mutate_input():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"addr": {"$ref": "#/$defs/Address"}},
        "required": ["addr"],
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            }
        },
    }
    original = copy.deepcopy(ir)
    dump_xml(ir)
    assert ir == original


def test_returns_str():
    ir = {"type": "object", "title": "D", "properties": {}, "required": []}
    assert isinstance(dump_xml(ir), str)


# ---------------------------------------------------------------------------
# Out-of-vocabulary keywords: drop vs reject
# ---------------------------------------------------------------------------


def test_format_is_dropped():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"email": {"type": "string", "format": "email"}},
        "required": ["email"],
    }
    xml = dump_xml(ir)
    assert "format" not in xml
    email = next(c for c in _parse(xml) if c.tag == "email")
    assert email.get("format") is None


def test_additional_properties_is_dropped():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    xml = dump_xml(ir)
    assert "additionalProperties" not in xml


def test_const_is_rejected():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"v": {"const": 5}},
        "required": ["v"],
    }
    with pytest.raises(SchemaError, match="const"):
        dump_xml(ir)


# ---------------------------------------------------------------------------
# Failure modes — messages must NOT mention "strict mode"
# ---------------------------------------------------------------------------


def _assert_not_strict(exc_info: pytest.ExceptionInfo[SchemaError]) -> None:
    assert "strict mode" not in str(exc_info.value)


def test_oneof_rejected():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"v": {"oneOf": [{"type": "string"}]}},
        "required": ["v"],
    }
    with pytest.raises(SchemaError, match="oneOf") as exc:
        dump_xml(ir)
    _assert_not_strict(exc)


def test_allof_rejected():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"v": {"allOf": [{"type": "string"}]}},
        "required": ["v"],
    }
    with pytest.raises(SchemaError, match="allOf") as exc:
        dump_xml(ir)
    _assert_not_strict(exc)


def test_non_null_anyof_rejected():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"v": {"anyOf": [{"type": "string"}, {"type": "integer"}]}},
        "required": ["v"],
    }
    with pytest.raises(SchemaError, match="anyOf") as exc:
        dump_xml(ir)
    _assert_not_strict(exc)


def test_cyclic_ref_rejected():
    ir = {
        "$ref": "#/$defs/Node",
        "$defs": {
            "Node": {
                "type": "object",
                "title": "Node",
                "properties": {"child": {"$ref": "#/$defs/Node"}},
                "required": [],
            }
        },
    }
    with pytest.raises(SchemaError, match=r"[Cc]yclic") as exc:
        dump_xml(ir)
    _assert_not_strict(exc)


def test_non_local_ref_rejected():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"v": {"$ref": "http://example.com/x"}},
        "required": ["v"],
    }
    with pytest.raises(SchemaError, match="local") as exc:
        dump_xml(ir)
    _assert_not_strict(exc)


def test_unresolvable_ref_rejected():
    ir = {
        "type": "object",
        "title": "Doc",
        "properties": {"v": {"$ref": "#/$defs/Missing"}},
        "required": ["v"],
        "$defs": {},
    }
    with pytest.raises(SchemaError, match="Missing") as exc:
        dump_xml(ir)
    _assert_not_strict(exc)
