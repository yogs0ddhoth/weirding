"""Reverse edge C → B: derive a JSON Schema IR from a Pydantic model.

``to_schema`` is the inverse of ``from_schema`` (ADR-0012). It normalizes
``model.model_json_schema()`` into weirding's JSON Schema IR rather than
reimplementing type extraction, so it tracks Pydantic's own type → schema logic
across releases.

The function is pure: it deep-copies Pydantic's schema output, never mutates the
model, and performs no I/O, logging, or network access — matching ``to_json_schema``
(ADR-0010). It deliberately leaves ``$defs`` / ``$ref`` intact; resolving them is
``dump_xml``'s concern, not this one (ADR-0012).
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

from weirding._exceptions import SchemaError
from weirding._itemtag import item_tag_fallback
from weirding._types import JsonSchemaIR


def to_schema(model: type[BaseModel]) -> JsonSchemaIR:
    """Derive a weirding JSON Schema IR from a Pydantic v2 model class.

    Normalizes ``model.model_json_schema()`` into IR. Array properties that
    lack the ``x-weirding-item-tag`` extension key (hand-written models that
    were not built by weirding) receive a synthesized tag via the shared
    singularization fallback, keyed on the property name. Models built by
    weirding's ``from_schema`` already carry ``x-weirding-item-tag`` through
    ``json_schema_extra``, so the fallback only fires for foreign models.

    ``$defs`` / ``$ref`` are left intact — Pydantic hoists nested models into
    ``$defs``, and resolving those references is ``dump_xml``'s job (ADR-0012).

    The model is never mutated; the function operates on a deep copy of
    Pydantic's schema output and returns a new dict.

    Args:
        model: A Pydantic v2 ``BaseModel`` subclass.

    Returns:
        A new JSON Schema IR dict. May contain ``$defs`` / ``$ref`` when the
        model has nested object fields.

    Raises:
        SchemaError: When the model's schema contains ``prefixItems`` (a tuple
            field), which is unrepresentable in the IR (ADR-0004, MEMORY rule
            11). The message names the offending path.
    """
    document: JsonSchemaIR = copy.deepcopy(model.model_json_schema())
    _walk(document, path="$", field_name=None)
    return document


def _walk(node: Any, *, path: str, field_name: str | None) -> None:
    """Recursively normalize *node* in place.

    Args:
        node: The current schema node (dict, list, or scalar).
        path: A human-readable JSON path to *node*, used in error messages.
        field_name: The name of the property *node* is the value of, or
            ``None`` when *node* is not a direct property value (e.g. the root,
            an ``items`` schema, or a ``$defs`` container).
    """
    if isinstance(node, dict):
        if "prefixItems" in node:
            raise SchemaError(
                f"Cannot derive IR: 'prefixItems' at {path} is unrepresentable "
                "in the weirding IR (tuple fields are banned; see ADR-0004). "
                "Replace the tuple field with a named-field object."
            )

        if (
            node.get("type") == "array"
            and field_name is not None
            and "x-weirding-item-tag" not in node
        ):
            node["x-weirding-item-tag"] = item_tag_fallback(field_name)

        properties = node.get("properties")
        if isinstance(properties, dict):
            # Canonical IR (compile_schema) always carries a ``required`` list on
            # every object node, even when empty. Pydantic's model_json_schema()
            # omits ``required`` entirely when no field is required, so restore
            # the invariant here to keep to_schema(from_schema(ir)) symmetric.
            if "required" not in node:
                node["required"] = []
            for prop_name, child in properties.items():
                _walk(
                    child, path=f"{path}.properties.{prop_name}", field_name=prop_name
                )

        defs = node.get("$defs")
        if isinstance(defs, dict):
            for def_name, child in defs.items():
                _walk(child, path=f"{path}.$defs.{def_name}", field_name=None)

        items = node.get("items")
        if isinstance(items, dict):
            _walk(items, path=f"{path}.items", field_name=None)

        for combiner in ("anyOf", "oneOf", "allOf"):
            members = node.get(combiner)
            if isinstance(members, list):
                for index, child in enumerate(members):
                    _walk(child, path=f"{path}.{combiner}[{index}]", field_name=None)

    elif isinstance(node, list):
        for index, child in enumerate(node):
            _walk(child, path=f"{path}[{index}]", field_name=None)
