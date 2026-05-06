from __future__ import annotations

from typing import Any

from lxml import etree

from weirding._exceptions import ParseError, UnsupportedDialectError
from weirding._parser import make_parser

# XSD namespace URI — root element in this namespace triggers UnsupportedDialectError
_XSD_NS = "http://www.w3.org/2001/XMLSchema"
_XSD_SCHEMA_TAG = f"{{{_XSD_NS}}}schema"

# Attribute names that control structural dispatch rather than JSON Schema keywords
_STRUCTURAL_ATTRS = frozenset({"type", "required", "nullable"})


# ---------------------------------------------------------------------------
# Attribute dispatch helpers
# ---------------------------------------------------------------------------


def _apply_attrs(element: etree._Element, schema: dict[str, Any]) -> None:
    """Apply element attributes to *schema* in-place, following the dispatch table.

    The ``type``, ``required``, and ``nullable`` attributes are handled by the
    caller and must not be double-emitted here.
    """
    attrib = element.attrib

    if "description" in attrib:
        schema["description"] = attrib["description"]

    if "enum" in attrib:
        schema["enum"] = [v for v in attrib["enum"].split("|")]

    if "pattern" in attrib:
        schema["pattern"] = attrib["pattern"]

    if "minimum" in attrib:
        schema["minimum"] = float(attrib["minimum"])

    if "maximum" in attrib:
        schema["maximum"] = float(attrib["maximum"])

    # ``min`` → minLength (string) or minItems (array)
    if "min" in attrib:
        current_type = attrib.get("type", "")
        if current_type == "array":
            schema["minItems"] = int(attrib["min"])
        else:
            schema["minLength"] = int(attrib["min"])

    # ``max`` → maxLength (string) or maxItems (array)
    if "max" in attrib:
        current_type = attrib.get("type", "")
        if current_type == "array":
            schema["maxItems"] = int(attrib["max"])
        else:
            schema["maxLength"] = int(attrib["max"])

    if "default" in attrib:
        schema["default"] = attrib["default"]


def _wrap_nullable(schema: dict[str, Any]) -> dict[str, Any]:
    """Wrap *schema* in an anyOf null-union as required by ``nullable="true"``."""
    return {"anyOf": [schema, {"type": "null"}]}


# ---------------------------------------------------------------------------
# Core recursive conversion
# ---------------------------------------------------------------------------


def _element_to_schema(element: etree._Element) -> dict[str, Any]:
    """Recursively convert *element* to a JSON Schema fragment."""
    attrib = element.attrib
    explicit_type = attrib.get("type", "")
    nullable = attrib.get("nullable", "").lower() == "true"
    children = list(element)

    # ── Array ────────────────────────────────────────────────────────────────
    if explicit_type == "array":
        schema: dict[str, Any] = {"type": "array"}
        _apply_attrs(element, schema)

        if children:
            child = children[0]
            schema["items"] = _element_to_schema(child)
            schema["x-weirding-item-tag"] = _local_tag(child)
        else:
            schema["items"] = {"type": "string"}

        if nullable:
            return _wrap_nullable(schema)
        return schema

    # ── Object — explicit or inferred from children ──────────────────────────
    if explicit_type == "object" or (not explicit_type and children):
        schema = {"type": "object"}
        _apply_attrs(element, schema)

        properties: dict[str, Any] = {}
        required: list[str] = []

        for child in children:
            tag = _local_tag(child)
            child_schema = _element_to_schema(child)
            properties[tag] = child_schema

            # Default is required; only omit when required="false" explicitly set
            if child.attrib.get("required", "true").lower() != "false":
                required.append(tag)

        schema["properties"] = properties
        schema["required"] = required

        if nullable:
            return _wrap_nullable(schema)
        return schema

    # ── Leaf (scalar) ─────────────────────────────────────────────────────────
    leaf_type = explicit_type if explicit_type else "string"
    schema = {"type": leaf_type}
    _apply_attrs(element, schema)

    if nullable:
        return _wrap_nullable(schema)
    return schema


def _local_tag(element: etree._Element) -> str:
    """Return the local (non-namespace-qualified) tag name of *element*."""
    tag = element.tag
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile_schema(xml: str | bytes) -> dict:
    """Parse an XML schema document into a JSON Schema IR dict.

    Uses the plain-attribute annotation convention. Never emits prefixItems —
    positional sequences are represented as named-field objects (MEMORY.md rule 11).
    """
    if not xml or (isinstance(xml, (str, bytes)) and not xml.strip()):
        raise ParseError("Empty input")

    parser = make_parser()

    try:
        if isinstance(xml, str):
            root = etree.fromstring(xml.encode(), parser=parser)
        else:
            root = etree.fromstring(xml, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ParseError(str(exc)) from exc

    if root.tag == _XSD_SCHEMA_TAG:
        raise UnsupportedDialectError("XSD support requires weirding[xsd]")

    root_tag = _local_tag(root)
    children = list(root)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for child in children:
        tag = _local_tag(child)
        child_schema = _element_to_schema(child)
        properties[tag] = child_schema

        if child.attrib.get("required", "true").lower() != "false":
            required.append(tag)

    return {
        "type": "object",
        "title": root_tag,
        "properties": properties,
        "required": required,
    }
