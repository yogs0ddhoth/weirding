"""XSD → JSON Schema IR bridge.

Converts an already-parsed lxml element tree rooted at xs:schema into the
weirding JSON Schema IR dict.  Security invariant: ``defuse="always"`` is
passed to every ``xmlschema.XMLSchema()`` call so that remote entity
references are always rejected regardless of the caller.

See ADR-0006 for library choice rationale, security posture, and type-map
key format (Clark-notation URIs, never xs:-prefixed names).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Any

import xmlschema
from lxml import etree

from weirding._exceptions import SchemaError
from weirding._types import JsonSchemaIR

_XSD_NS = "http://www.w3.org/2001/XMLSchema"


def _xsd_key(local: str) -> str:
    return f"{{{_XSD_NS}}}{local}"


# ---------------------------------------------------------------------------
# Type map — keys are Clark-notation URIs (NOT xs:-prefixed names)
# ---------------------------------------------------------------------------

_XSD_TYPE_MAP: dict[str, JsonSchemaIR] = {
    # string-like
    **{
        _xsd_key(t): {"type": "string"}
        for t in [
            "string",
            "normalizedString",
            "token",
            "anyURI",
            "ID",
            "IDREF",
            "Name",
            "NCName",
            "NMTOKEN",
            "duration",
            "gYear",
            "gMonth",
            "gDay",
            "hexBinary",
            "base64Binary",
        ]
    },
    # integer-like
    **{
        _xsd_key(t): {"type": "integer"}
        for t in [
            "integer",
            "int",
            "long",
            "short",
            "byte",
            "nonNegativeInteger",
            "positiveInteger",
            "unsignedInt",
            "unsignedLong",
            "unsignedShort",
            "unsignedByte",
        ]
    },
    # number-like
    **{_xsd_key(t): {"type": "number"} for t in ["decimal", "float", "double"]},
    # boolean
    _xsd_key("boolean"): {"type": "boolean"},
    # date/time with format
    _xsd_key("date"): {"type": "string", "format": "date"},
    _xsd_key("time"): {"type": "string", "format": "time"},
    _xsd_key("dateTime"): {"type": "string", "format": "date-time"},
}


def _primitive_to_ir(xsd_type: Any) -> JsonSchemaIR:
    """Map an xmlschema type object to a JSON Schema IR fragment."""
    name = getattr(xsd_type, "name", None)
    if name is None:
        return {"type": "string"}
    return dict(_XSD_TYPE_MAP.get(name, {"type": "string"}))


# ---------------------------------------------------------------------------
# Iteration helpers
# ---------------------------------------------------------------------------


def _iter_elements(complex_type: Any):
    """Yield element declarations from a complex type's model group.

    Guards against xs:simpleContent (content is not a group — not iterable).
    """
    from xmlschema.validators import XsdGroup

    content = getattr(complex_type, "content", None)
    if not isinstance(content, XsdGroup):
        return
    yield from content


# ---------------------------------------------------------------------------
# Type dispatch
# ---------------------------------------------------------------------------


def _type_to_schema(xsd_type: Any) -> JsonSchemaIR:
    """Convert an xmlschema type object to a JSON Schema IR fragment."""
    from xmlschema.validators import XsdComplexType

    # Enum: restriction with enumeration facets
    if hasattr(xsd_type, "enumeration") and xsd_type.enumeration:
        base_ir = (
            _primitive_to_ir(xsd_type.base_type)
            if hasattr(xsd_type, "base_type")
            else {"type": "string"}
        )
        return {**base_ir, "enum": list(xsd_type.enumeration)}

    # Complex type → object
    if isinstance(xsd_type, XsdComplexType):
        return _complex_type_to_ir(xsd_type)

    # Scalar
    return _primitive_to_ir(xsd_type)


def _choice_to_ir(choice_group: Any) -> JsonSchemaIR:
    """Convert an xs:choice group to a JSON Schema oneOf."""
    branches = []
    for elem_decl in choice_group:
        field_name = elem_decl.local_name
        field_ir = _elem_decl_to_ir(elem_decl)
        branch = {
            "type": "object",
            "properties": {field_name: field_ir},
            "required": [field_name],
        }
        branches.append(branch)
    return {"oneOf": branches}


def _complex_type_to_ir(complex_type: Any) -> JsonSchemaIR:
    """Convert an XsdComplexType to a JSON Schema object fragment."""
    from xmlschema.validators import XsdGroup

    content = getattr(complex_type, "content", None)
    if not isinstance(content, XsdGroup):
        return _primitive_to_ir(complex_type)

    if content.model == "choice":
        return _choice_to_ir(content)

    properties: dict[str, JsonSchemaIR] = {}
    required: list[str] = []

    for elem_decl in _iter_elements(complex_type):
        field_name = elem_decl.local_name
        if field_name is None:
            continue
        field_ir = _elem_decl_to_ir(elem_decl)

        # xs:annotation/xs:documentation → description
        annotation = getattr(elem_decl, "annotation", None)
        if annotation is not None:
            docs = getattr(annotation, "documentation", None)
            if docs:
                doc_list = list(docs)
                if doc_list:
                    field_ir["description"] = str(doc_list[0])

        # nillable="true" → anyOf null-union
        if getattr(elem_decl, "nillable", False):
            field_ir = {"anyOf": [field_ir, {"type": "null"}]}

        properties[field_name] = field_ir

        min_occurs = getattr(elem_decl, "min_occurs", 1)
        if min_occurs != 0:
            required.append(field_name)

    schema: JsonSchemaIR = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _elem_decl_to_ir(elem_decl: Any) -> JsonSchemaIR:
    """Convert an element declaration to a JSON Schema IR fragment.

    Handles arrays (maxOccurs > 1 or unbounded) and delegates to
    _type_to_schema for complex types and scalars.
    """
    xsd_type = elem_decl.type
    max_occurs = getattr(elem_decl, "max_occurs", 1)

    # Array: maxOccurs > 1 or unbounded (None)
    if max_occurs is None or (isinstance(max_occurs, int) and max_occurs > 1):
        item_ir = _type_to_schema(xsd_type)
        array_ir: JsonSchemaIR = {
            "type": "array",
            "items": item_ir,
            "x-weirding-item-tag": elem_decl.local_name,
        }
        min_occurs = getattr(elem_decl, "min_occurs", 0)
        if min_occurs and min_occurs > 0:
            array_ir["minItems"] = min_occurs
        if max_occurs is not None:
            array_ir["maxItems"] = max_occurs
        return array_ir

    return _type_to_schema(xsd_type)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def xsd_to_ir(root: etree._Element) -> JsonSchemaIR:
    """Convert an xs:schema lxml element to a JSON Schema IR dict.

    Args:
        root: An already-parsed lxml element rooted at xs:schema.

    Returns:
        JSON Schema-compatible dict (draft 2020-12 subset).

    Raises:
        SchemaError: The XSD has no top-level element declarations, or the
                     document is structurally invalid.

    """
    try:
        xs = xmlschema.XMLSchema(root, defuse="always")
    except xmlschema.XMLSchemaParseError as exc:
        raise SchemaError(str(exc)) from exc

    if not xs.elements:
        raise SchemaError("XSD has no top-level element declarations")

    root_elem = next(iter(xs.elements.values()))
    title = root_elem.local_name

    schema = _type_to_schema(root_elem.type)
    schema["title"] = title
    return schema
