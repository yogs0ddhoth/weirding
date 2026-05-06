from __future__ import annotations

import re
from typing import Any, Protocol, overload, runtime_checkable

from lxml import etree
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from weirding._exceptions import (
    ParseError,
    SchemaError,
    UnsupportedDialectError,
    WeirdingError,
)
from weirding._parser import make_parser
from weirding._schema import compile_schema
from weirding._serializers import _xml_to_dict
from weirding._serializers import to_xml as _to_xml

__all__ = [
    "DTOBuilder",
    "ParseError",
    "PydanticBuilder",
    "SchemaError",
    "UnsupportedDialectError",
    "Validatable",
    "WeirdingError",
    "compile",
    "define_model",
    "from_schema",
    "parse",
    "to_xml",
]

_NAME_RE = re.compile(r"[^A-Za-z0-9_]")
_LEADING_DIGITS_RE = re.compile(r"^[0-9]+")


def _sanitize_name(tag: str) -> str:
    name = _NAME_RE.sub("_", tag)
    name = _LEADING_DIGITS_RE.sub("", name)
    return name or "Model"


@runtime_checkable
class Validatable(Protocol):
    """Any type that can validate a dict into a typed instance.

    Satisfied by every Pydantic BaseModel subclass. Accepting a Protocol
    instead of BaseModel directly keeps parse() open to non-Pydantic backends
    (TypeAdapter wrappers, Spark schema validators, etc.) without an API change.
    """

    @classmethod
    def model_validate(cls, obj: dict[str, Any]) -> Any: ...


@runtime_checkable
class DTOBuilder(Protocol):
    """Any type that can build a typed DTO class from a JSON Schema IR dict.

    The default implementation is PydanticBuilder, which produces Pydantic v2
    BaseModel subclasses. Custom implementations can produce TypedDicts,
    dataclasses, Spark StructType wrappers, or any other typed container.

    Symmetric with Validatable: both ends of the pipeline are backend-neutral.
    Pydantic is the default, not the requirement.
    """

    def build(self, schema: dict, *, name: str) -> type: ...


class PydanticBuilder:
    """Default DTOBuilder — produces Pydantic v2 BaseModel subclasses.

    Engine: json-schema-to-pydantic. Patches applied:
      - schema["additionalProperties"] == False  →  model_config extra="forbid"
      - prefixItems must never appear in schema (enforced by _schema.py)
    """

    def build(self, schema: dict, *, name: str = "Model") -> type[BaseModel]:
        from weirding._models import build_model

        return build_model(schema, name=name)


def compile(xml: str | bytes) -> dict:
    """Convert an XML schema document to a JSON Schema IR dict.

    The JSON Schema dict is the core product of weirding. It can be consumed
    directly (Databricks StructType, jsonschema.validate, OpenAPI specs) or
    passed to from_schema() to build a typed DTO.

    Args:
        xml: XML schema document using the plain-attribute annotation convention
             or XSD. XSD requires the weirding[xsd] extra.

    Returns:
        JSON Schema-compatible dict (draft 2020-12 subset). Array fields include
        an x-weirding-item-tag extension key naming the child element tag.

    Raises:
        SchemaError: schema document is structurally invalid.
        UnsupportedDialectError: dialect cannot be detected or is unsupported.
        ParseError: xml is not well-formed.
    """
    return compile_schema(xml)


@overload
def from_schema(schema: dict, *, name: str = ...) -> type[BaseModel]: ...


@overload
def from_schema(
    schema: dict, *, name: str = ..., builder: DTOBuilder
) -> type: ...


def from_schema(
    schema: dict,
    *,
    name: str = "Model",
    builder: DTOBuilder | None = None,
) -> type:
    """Build a typed DTO class from a JSON Schema IR dict.

    With the default builder (PydanticBuilder), returns a Pydantic v2
    BaseModel subclass. Pass a custom DTOBuilder to produce TypedDicts,
    dataclasses, Spark StructType wrappers, or any other typed container.

    Args:
        schema:  JSON Schema dict as produced by compile() or any compatible source.
        name:    Class name for the generated type. Must be a valid Python identifier.
        builder: DTOBuilder implementation. Defaults to PydanticBuilder().

    Returns:
        A new type produced by the builder. Each call with a distinct schema produces
        a distinct class; cache the result if calling in a hot path.

    Raises:
        SchemaError: schema cannot be converted to a valid typed class.
    """
    return (builder or PydanticBuilder()).build(schema, name=name)


def define_model(
    xml: str | bytes,
    *,
    builder: DTOBuilder | None = None,
) -> type:
    """Convenience: compile(xml) then from_schema(), naming the type from the root tag.

    Equivalent to:
        schema = compile(xml)
        return from_schema(schema, name=<sanitized root element tag>, builder=builder)

    Args:
        xml:     XML schema document (plain-attribute convention or XSD).
        builder: DTOBuilder implementation. Defaults to PydanticBuilder().

    Returns:
        A new type produced by the builder.
    """
    schema = compile(xml)
    name = _sanitize_name(schema.get("title", "Model"))
    return from_schema(schema, name=name, builder=builder)


def parse(xml: str | bytes, model: type[Validatable]) -> Any:
    """Validate and bind LLM-produced XML against a compiled model.

    Deserializes the XML element tree into a dict, then calls
    model.model_validate(dict) to produce a typed instance.

    Args:
        xml:   XML data document (LLM output). Must be well-formed.
        model: Any type satisfying the Validatable protocol — in practice a
               type produced by define_model() or from_schema().

    Returns:
        A validated instance of model.

    Raises:
        ParseError: xml is malformed or fails model validation.
    """
    parser = make_parser()
    try:
        if isinstance(xml, str):
            root = etree.fromstring(xml.encode(), parser=parser)
        else:
            root = etree.fromstring(xml, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ParseError(str(exc)) from exc

    data = _xml_to_dict(root, model)  # type: ignore[arg-type]
    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        raise ParseError(str(exc)) from exc


def to_xml(instance: BaseModel) -> str:
    """Serialize a Pydantic model instance to an XML string.

    Element tags map to field names, scalars become text content, objects become
    child elements, and lists are serialized as repeated child elements using the
    tag name from the original schema (x-weirding-item-tag).

    Round-trip guarantee: parse(to_xml(x), type(x)) == x for any instance x
    produced by parse().

    Args:
        instance: Any Pydantic BaseModel instance, including dynamically generated ones.

    Returns:
        UTF-8 XML string without an XML declaration.
    """
    return _to_xml(instance)
