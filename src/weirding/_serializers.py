from __future__ import annotations

from typing import Any, get_args, get_origin

from lxml import etree
from pydantic import BaseModel
from pydantic.fields import FieldInfo

# ---------------------------------------------------------------------------
# Scalar rendering
# ---------------------------------------------------------------------------


def _render_scalar(value: Any) -> str:
    """Convert a Python scalar to its XML text representation.

    bool → "true" / "false" (not Python's True/False).
    Everything else → str(value).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Item-tag resolution helpers
# ---------------------------------------------------------------------------


def _item_tag_for_field(field_name: str, field_info: FieldInfo) -> str:
    """Return the XML child tag for list items of *field_name*.

    Priority:
    1. ``x-weirding-item-tag`` from the field's json_schema_extra dict.
    2. Field name with a trailing ``s`` stripped (e.g. ``tags`` → ``tag``).
    3. Literal ``"item"`` when the field name has no trailing ``s``.
    """
    if isinstance(field_info.json_schema_extra, dict):
        tag = field_info.json_schema_extra.get("x-weirding-item-tag")
        if tag:
            return tag

    # Fallback: strip trailing "s", or use "item"
    if field_name.endswith("s") and len(field_name) > 1:
        return field_name[:-1]
    return "item"


# ---------------------------------------------------------------------------
# Core recursive builder
# ---------------------------------------------------------------------------


def _append_field(parent: etree._Element, tag: str, value: Any, item_tag: str) -> None:
    """Append a child element <tag> to *parent* and populate it from *value*.

    Dispatch:
    - None       → self-closing <tag/>
    - BaseModel  → recurse into nested model
    - list       → repeated <item_tag> children
    - scalar     → text content
    """
    elem = etree.SubElement(parent, tag)

    if value is None:
        return  # self-closing

    if isinstance(value, BaseModel):
        _populate_element(elem, value)
    elif isinstance(value, list):
        for item in value:
            child = etree.SubElement(elem, item_tag)
            if item is None:
                pass  # self-closing
            elif isinstance(item, BaseModel):
                _populate_element(child, item)
            else:
                child.text = _render_scalar(item)
    else:
        elem.text = _render_scalar(value)


def _populate_element(elem: etree._Element, instance: BaseModel) -> None:
    """Populate *elem* with child elements for each field in *instance*.

    Accesses field values directly from the instance (not via model_dump()) so
    that nested BaseModel instances are preserved as BaseModel objects rather
    than being coerced to plain dicts.
    """
    model_cls = type(instance)
    for field_name in model_cls.model_fields:
        value = getattr(instance, field_name, None)
        field_info_obj = model_cls.model_fields[field_name]
        item_tag = _item_tag_for_field(field_name, field_info_obj)
        _append_field(elem, field_name, value, item_tag)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def to_xml(instance: BaseModel) -> str:
    """Serialize a Pydantic v2 BaseModel instance to an XML string.

    Root element tag is the model class ``__name__``.
    Returns a UTF-8 XML string without an XML declaration.
    """
    root_tag = instance.__class__.__name__
    root = etree.Element(root_tag)
    _populate_element(root, instance)
    return etree.tostring(root, encoding="unicode")


# ---------------------------------------------------------------------------
# Internal deserializer (imported by parse() in __init__.py)
# ---------------------------------------------------------------------------


def _is_list_field(annotation: Any) -> bool:
    """Return True if *annotation* is list[...] or List[...]."""
    return get_origin(annotation) is list


def _xml_to_dict(element: etree._Element, model_type: type) -> dict[str, Any]:
    """Convert an lxml element tree into a dict for ``model_type.model_validate()``.

    Uses ``model_type.model_fields`` to drive the conversion — schema-aware, not
    naive same-tag coalescing.

    Returns a dict of ``{field_name: value}`` derived from *element*'s children.
    """
    result: dict[str, Any] = {}

    # Build a tag → list-of-elements map from the children of *element*
    children_by_tag: dict[str, list[etree._Element]] = {}
    for child in element:
        tag = child.tag
        if isinstance(tag, str):  # skip processing instructions / comments
            children_by_tag.setdefault(tag, []).append(child)

    for field_name, field_info in model_type.model_fields.items():
        annotation = field_info.annotation
        child_elements = children_by_tag.get(field_name, [])

        if _is_list_field(annotation):
            # List field — the field element wraps repeated child elements.
            if child_elements:
                wrapper = child_elements[0]
                item_type_args = get_args(annotation)
                item_type = item_type_args[0] if item_type_args else None
                items: list[Any] = []
                for item_elem in wrapper:
                    if not isinstance(item_elem.tag, str):
                        continue
                    if (
                        item_type is not None
                        and isinstance(item_type, type)
                        and issubclass(item_type, BaseModel)
                    ):
                        items.append(_xml_to_dict(item_elem, item_type))
                    else:
                        items.append(item_elem.text or "")
                result[field_name] = items
            else:
                result[field_name] = []

        elif (
            annotation is not None
            and isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
        ):
            # Nested object field — recurse with the nested model type.
            if child_elements:
                result[field_name] = _xml_to_dict(child_elements[0], annotation)
            # Absent optional nested field: omit the key so Pydantic's default triggers.

        else:
            # Scalar field
            if child_elements:
                elem = child_elements[0]
                text = elem.text
                if text is None:
                    # Empty element — required or not?
                    required = field_info.is_required()
                    result[field_name] = "" if required else None
                else:
                    result[field_name] = text
            elif field_info.is_required():
                # Required field absent from XML: pass None so Pydantic
                # raises a clear validation error.
                result[field_name] = None
            # Optional absent field: omit key so Pydantic's default triggers.

    return result
