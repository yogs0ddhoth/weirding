"""Tests for to_xml() and _xml_to_dict() in weirding._serializers."""

from __future__ import annotations

from lxml import etree
from pydantic import BaseModel

from weirding._models import build_model
from weirding._schema import compile_schema
from weirding._serializers import _xml_to_dict, to_xml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_xml(xml_str: str) -> etree._Element:
    return etree.fromstring(xml_str.encode())


# ---------------------------------------------------------------------------
# 1. to_xml — flat model: string and int fields
# ---------------------------------------------------------------------------


def test_to_xml_flat_model() -> None:
    class Person(BaseModel):
        name: str
        age: int

    instance = Person(name="Alice", age=30)
    xml_str = to_xml(instance)
    root = _parse_xml(xml_str)
    assert root.tag == "Person"
    name_elem = root.find("name")
    age_elem = root.find("age")
    assert name_elem is not None and name_elem.text == "Alice"
    assert age_elem is not None and age_elem.text == "30"


# ---------------------------------------------------------------------------
# 2. to_xml — nested model
# ---------------------------------------------------------------------------


def test_to_xml_nested_model() -> None:
    class Address(BaseModel):
        street: str
        city: str

    class Order(BaseModel):
        address: Address

    instance = Order(address=Address(street="Main St", city="Springfield"))
    xml_str = to_xml(instance)
    root = _parse_xml(xml_str)
    assert root.tag == "Order"
    addr_elem = root.find("address")
    assert addr_elem is not None
    street_elem = addr_elem.find("street")
    city_elem = addr_elem.find("city")
    assert street_elem is not None and street_elem.text == "Main St"
    assert city_elem is not None and city_elem.text == "Springfield"


# ---------------------------------------------------------------------------
# 3. to_xml — list field with x-weirding-item-tag from define_model
# ---------------------------------------------------------------------------


def test_to_xml_list_field_item_tag_from_schema() -> None:
    """List items use the x-weirding-item-tag stored in the JSON schema."""
    xml_schema = "<Response><tags type='array'><tag /></tags></Response>"
    schema = compile_schema(xml_schema)
    Model = build_model(schema, name="Response")

    instance = Model.model_validate({"tags": ["alpha", "beta", "gamma"]})
    xml_str = to_xml(instance)
    root = _parse_xml(xml_str)
    tags_elem = root.find("tags")
    assert tags_elem is not None
    children = list(tags_elem)
    assert len(children) == 3
    assert all(c.tag == "tag" for c in children)
    assert [c.text for c in children] == ["alpha", "beta", "gamma"]


# ---------------------------------------------------------------------------
# 4. to_xml — None field → empty element
# ---------------------------------------------------------------------------


def test_to_xml_none_field() -> None:
    class Profile(BaseModel):
        username: str
        bio: str | None = None

    instance = Profile(username="alice", bio=None)
    xml_str = to_xml(instance)
    root = _parse_xml(xml_str)
    bio_elem = root.find("bio")
    assert bio_elem is not None
    assert bio_elem.text is None  # empty / self-closing


# ---------------------------------------------------------------------------
# 5. to_xml — bool field serialized as "true" / "false"
# ---------------------------------------------------------------------------


def test_to_xml_bool_true() -> None:
    class Flags(BaseModel):
        active: bool

    xml_str = to_xml(Flags(active=True))
    root = _parse_xml(xml_str)
    active_elem = root.find("active")
    assert active_elem is not None and active_elem.text == "true"


def test_to_xml_bool_false() -> None:
    class Flags(BaseModel):
        active: bool

    xml_str = to_xml(Flags(active=False))
    root = _parse_xml(xml_str)
    active_elem = root.find("active")
    assert active_elem is not None and active_elem.text == "false"


# ---------------------------------------------------------------------------
# 6. _xml_to_dict — flat element
# ---------------------------------------------------------------------------


def test_xml_to_dict_flat() -> None:
    class Item(BaseModel):
        name: str
        count: int

    xml_str = "<Item><name>Widget</name><count>5</count></Item>"
    elem = _parse_xml(xml_str)
    d = _xml_to_dict(elem, Item)
    assert d == {"name": "Widget", "count": "5"}


# ---------------------------------------------------------------------------
# 7. _xml_to_dict — list field: repeated same-tag children → list in dict
# ---------------------------------------------------------------------------


def test_xml_to_dict_list_field() -> None:
    xml_schema = "<Response><tags type='array'><tag /></tags></Response>"
    schema = compile_schema(xml_schema)
    Model = build_model(schema, name="Response")

    xml_str = "<Response><tags><tag>a</tag><tag>b</tag><tag>c</tag></tags></Response>"
    elem = _parse_xml(xml_str)
    d = _xml_to_dict(elem, Model)
    assert d["tags"] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# 8. Round-trip — flat model
# ---------------------------------------------------------------------------


def test_roundtrip_flat() -> None:
    xml_schema = "<Person><name /><age type='integer' /></Person>"
    schema = compile_schema(xml_schema)
    Model = build_model(schema, name="Person")

    original = Model.model_validate({"name": "Bob", "age": 42})
    xml_str = to_xml(original)
    elem = _parse_xml(xml_str)
    d = _xml_to_dict(elem, Model)
    restored = Model.model_validate(d)
    assert restored.name == original.name  # type: ignore[attr-defined]
    # age is returned as string from XML text; coercion happens in model_validate
    assert restored.age == original.age  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 8b. Round-trip — nested model
# ---------------------------------------------------------------------------


def test_roundtrip_nested() -> None:
    xml_schema = '<Order><customer><name /><age type="integer" /></customer></Order>'
    schema = compile_schema(xml_schema)
    Model = build_model(schema, name="Order")

    original = Model.model_validate({"customer": {"name": "Carol", "age": 35}})
    xml_str = to_xml(original)
    elem = _parse_xml(xml_str)
    d = _xml_to_dict(elem, Model)
    restored = Model.model_validate(d)
    assert restored.customer.name == original.customer.name  # type: ignore[attr-defined]
    assert restored.customer.age == original.customer.age  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 8c. Round-trip — list field
# ---------------------------------------------------------------------------


def test_roundtrip_list() -> None:
    xml_schema = "<Response><tags type='array'><tag /></tags></Response>"
    schema = compile_schema(xml_schema)
    Model = build_model(schema, name="Response")

    original = Model.model_validate({"tags": ["x", "y", "z"]})
    xml_str = to_xml(original)
    elem = _parse_xml(xml_str)
    d = _xml_to_dict(elem, Model)
    restored = Model.model_validate(d)
    assert restored.tags == original.tags  # type: ignore[attr-defined]
