"""Tests for XSD → JSON Schema IR bridge (weirding[xsd])."""

import pytest

from weirding import compile, from_schema, parse, to_xml
from weirding._exceptions import SchemaError

xmlschema = pytest.importorskip("xmlschema")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FLAT_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Person">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="name" type="xs:string"/>
        <xs:element name="age" type="xs:integer"/>
        <xs:element name="score" type="xs:decimal"/>
        <xs:element name="active" type="xs:boolean"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

NESTED_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Order">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="id" type="xs:string"/>
        <xs:element name="customer" minOccurs="0">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="name" type="xs:string"/>
              <xs:element name="email" type="xs:anyURI"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

NILLABLE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Record">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="value" type="xs:string" nillable="true"/>
        <xs:element name="count" type="xs:integer"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

ARRAY_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Catalog">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item" type="xs:string" maxOccurs="unbounded"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

ENUM_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:simpleType name="StatusType">
    <xs:restriction base="xs:string">
      <xs:enumeration value="pending"/>
      <xs:enumeration value="active"/>
      <xs:enumeration value="closed"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:element name="Task">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="status" type="StatusType"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

DATE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Event">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="start_date" type="xs:date"/>
        <xs:element name="start_time" type="xs:time"/>
        <xs:element name="created_at" type="xs:dateTime"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

EMPTY_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
</xs:schema>
"""

CHOICE_XSD = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Shape">
    <xs:complexType>
      <xs:choice>
        <xs:element name="circle" type="xs:string"/>
        <xs:element name="rectangle" type="xs:string"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

# ---------------------------------------------------------------------------
# Phase 03a — flat scalar fields
# ---------------------------------------------------------------------------


class TestFlatXSD:
    def test_title(self):
        ir = compile(FLAT_XSD)
        assert ir["title"] == "Person"

    def test_type_is_object(self):
        ir = compile(FLAT_XSD)
        assert ir["type"] == "object"

    def test_string_property(self):
        ir = compile(FLAT_XSD)
        assert ir["properties"]["name"] == {"type": "string"}

    def test_integer_property(self):
        ir = compile(FLAT_XSD)
        assert ir["properties"]["age"] == {"type": "integer"}

    def test_decimal_maps_to_number(self):
        ir = compile(FLAT_XSD)
        assert ir["properties"]["score"] == {"type": "number"}

    def test_boolean_property(self):
        ir = compile(FLAT_XSD)
        assert ir["properties"]["active"] == {"type": "boolean"}

    def test_all_fields_required(self):
        ir = compile(FLAT_XSD)
        assert set(ir["required"]) == {"name", "age", "score", "active"}

    def test_empty_xsd_raises_schema_error(self):
        with pytest.raises(SchemaError):
            compile(EMPTY_XSD)


class TestDateTimeFormats:
    def test_date_format(self):
        ir = compile(DATE_XSD)
        assert ir["properties"]["start_date"] == {
            "type": "string", "format": "date"}

    def test_time_format(self):
        ir = compile(DATE_XSD)
        assert ir["properties"]["start_time"] == {
            "type": "string", "format": "time"}

    def test_datetime_format(self):
        ir = compile(DATE_XSD)
        assert ir["properties"]["created_at"] == {
            "type": "string",
            "format": "date-time",
        }


# ---------------------------------------------------------------------------
# Phase 03b — nested objects, optional fields, nillable
# ---------------------------------------------------------------------------


class TestNestedXSD:
    def test_nested_object_type(self):
        ir = compile(NESTED_XSD)
        assert ir["properties"]["customer"]["type"] == "object"

    def test_optional_field_not_in_required(self):
        ir = compile(NESTED_XSD)
        assert "customer" not in ir["required"]

    def test_required_field_in_required(self):
        ir = compile(NESTED_XSD)
        assert "id" in ir["required"]

    def test_any_uri_maps_to_string(self):
        ir = compile(NESTED_XSD)
        customer = ir["properties"]["customer"]
        assert customer["properties"]["email"] == {"type": "string"}


class TestNillable:
    def test_nillable_field_is_null_union(self):
        ir = compile(NILLABLE_XSD)
        assert ir["properties"]["value"] == {
            "anyOf": [{"type": "string"}, {"type": "null"}]
        }

    def test_non_nillable_field_unchanged(self):
        ir = compile(NILLABLE_XSD)
        assert ir["properties"]["count"] == {"type": "integer"}


# ---------------------------------------------------------------------------
# Phase 03c — arrays and enumerations
# ---------------------------------------------------------------------------


class TestArrayXSD:
    def test_array_type(self):
        ir = compile(ARRAY_XSD)
        assert ir["properties"]["item"]["type"] == "array"

    def test_array_items(self):
        ir = compile(ARRAY_XSD)
        assert ir["properties"]["item"]["items"] == {"type": "string"}

    def test_array_item_tag_extension(self):
        ir = compile(ARRAY_XSD)
        assert ir["properties"]["item"]["x-weirding-item-tag"] == "item"


class TestEnumXSD:
    def test_enum_values(self):
        ir = compile(ENUM_XSD)
        assert ir["properties"]["status"]["enum"] == [
            "pending", "active", "closed"]

    def test_enum_base_type(self):
        ir = compile(ENUM_XSD)
        # status is a string restriction — base type should map to string
        assert ir["properties"]["status"]["type"] == "string"


# ---------------------------------------------------------------------------
# Phase 03d — xs:choice → oneOf
# ---------------------------------------------------------------------------


class TestChoiceXSD:
    def test_choice_produces_one_of(self):
        ir = compile(CHOICE_XSD)
        assert "oneOf" in ir

    def test_choice_branch_count(self):
        ir = compile(CHOICE_XSD)
        assert len(ir["oneOf"]) == 2

    def test_first_branch_circle(self):
        ir = compile(CHOICE_XSD)
        branch = ir["oneOf"][0]
        assert "circle" in branch["properties"]
        assert branch["required"] == ["circle"]

    def test_second_branch_rectangle(self):
        ir = compile(CHOICE_XSD)
        branch = ir["oneOf"][1]
        assert "rectangle" in branch["properties"]
        assert branch["required"] == ["rectangle"]

    def test_branch_property_type(self):
        ir = compile(CHOICE_XSD)
        assert ir["oneOf"][0]["properties"]["circle"] == {"type": "string"}
        assert ir["oneOf"][1]["properties"]["rectangle"] == {"type": "string"}


# ---------------------------------------------------------------------------
# Integration: compile → from_schema → parse → to_xml
# ---------------------------------------------------------------------------


class TestFlatXSDRoundTrip:
    def test_flat_xsd_round_trip(self):
        ir = compile(FLAT_XSD)
        Model = from_schema(ir, name=ir["title"])
        xml_data = (
            "<Person><name>Alice</name><age>30</age>"
            "<score>9.5</score><active>true</active></Person>"
        )
        instance = parse(xml_data, Model)
        assert instance.name == "Alice"
        assert instance.age == 30
        result = to_xml(instance)
        assert "<name>Alice</name>" in result

    def test_nested_xsd_round_trip(self):
        ir = compile(NESTED_XSD)
        Model = from_schema(ir, name=ir["title"])
        xml_data = (
            "<Order><id>ORD-1</id>"
            "<customer><name>Bob</name><email>bob@example.com</email></customer></Order>"
        )
        instance = parse(xml_data, Model)
        assert instance.id == "ORD-1"
        assert instance.customer.name == "Bob"
