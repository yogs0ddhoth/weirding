"""Reverse edge B → A: serialize a JSON Schema IR back to XML schema.

:func:`dump_xml` is the structural inverse of
:func:`weirding._schema.compile_schema`. It emits a canonical ADR-0001
plain-attribute annotation XML *schema document* from the public
``JsonSchemaIR`` dict. See ADR-0012 for the decision and its documented limits.

It is a **pure** function: it deep-copies its input, never mutates it, and
performs no I/O, logging, or network access — matching ``to_json_schema``
(ADR-0010) and the project logging policy.

``dump_xml`` is a *partial* function. The annotation convention has no syntax
for non-null unions and no reference mechanism, so non-null
``anyOf``/``oneOf``/``allOf`` and cyclic/unresolvable ``$ref`` raise
:class:`weirding._exceptions.SchemaError` naming the construct rather than
emitting silently-wrong XML.
"""

from __future__ import annotations

import copy
from typing import Any

from lxml import etree

from weirding import _refs
from weirding._exceptions import SchemaError
from weirding._types import JsonSchemaIR

# IR scalar-constraint key → XML attribute name. Values are stringified.
# ``minimum``/``maximum`` are floats in canonical IR; ``str(float)`` round-trips
# through ``compile`` (which re-applies ``float()``). ``default`` is already a
# string in canonical IR, so ``str`` is a no-op there.
_SCALAR_ATTRS: tuple[str, ...] = (
    "description",
    "pattern",
    "minimum",
    "maximum",
    "default",
)

# Out-of-vocabulary keywords are handled by *allowlist emission*: the emitter
# only ever writes the attributes it knows. ``format`` and
# ``additionalProperties`` therefore drop silently (lossy but non-fatal,
# mirroring the strict-export drops in ADR-0010), while ``const`` is rejected
# explicitly in :func:`_emit_schema` because dropping it would silently lose a
# value constraint rather than a presentational hint.


def dump_xml(ir: JsonSchemaIR) -> str:
    """Serialize a JSON Schema IR dict to a canonical XML schema document.

    The inverse of :func:`weirding.compile`. Any local ``$ref`` / ``$defs`` are
    inlined first; the root element name is taken from ``ir['title']``
    (falling back to ``"Model"``).

    Args:
        ir: A JSON Schema IR dict, as produced by :func:`weirding.compile` or
            any compatible source. Must be acyclic and free of non-null unions.

    Returns:
        A pretty-printed XML schema document (``encoding='unicode'``) using the
        ADR-0001 plain-attribute annotation convention.

    Raises:
        SchemaError: The IR contains a construct with no annotation-convention
            representation — a non-null ``anyOf`` / ``oneOf`` / ``allOf``, a
            ``const``, or a cyclic / non-local / unresolvable ``$ref``. The
            message names the offending construct.
    """
    document = copy.deepcopy(ir)

    defs = document.get("$defs")
    defs_map: dict[str, Any] = defs if isinstance(defs, dict) else {}

    # Resolve a root-level $ref before deriving the element name.
    root_schema, root_seen = _inline(document, defs_map, _frozen_path())
    if not isinstance(root_schema, dict):
        raise SchemaError("Root schema is not a schema object.")

    title = root_schema.get("title")
    root_name = title if isinstance(title, str) and title else "Model"

    root = etree.Element(root_name)
    _emit_object_children(root, root_schema, defs_map, root_seen)

    return etree.tostring(root, encoding="unicode", pretty_print=True)


# ---------------------------------------------------------------------------
# Ref inlining + cycle detection
# ---------------------------------------------------------------------------


def _frozen_path() -> frozenset[str]:
    """Return an empty ref-visitation path for cycle detection."""
    return frozenset()


def _inline(
    node: dict[str, Any], defs_map: dict[str, Any], seen: frozenset[str]
) -> tuple[dict[str, Any], frozenset[str]]:
    """Inline a top-level ``$ref`` on *node*, detecting cycles.

    Only the immediate node is resolved; nested schemas are inlined lazily as
    the emitter descends into them. *seen* carries the chain of ``$ref`` targets
    already being resolved on this path so a cycle raises instead of recursing
    forever.

    Returns the resolved node together with the updated *seen* set, which the
    caller must thread into recursion so a ref reached again deeper down is
    recognized as a cycle.
    """
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str):
            raise SchemaError(f"$ref value {ref!r} is not a string.")
        if ref in seen:
            raise SchemaError(
                f"Cyclic $ref {ref!r}: cannot serialize a self-referential "
                "schema into a finite XML tree."
            )
        node = _refs.resolve_ref(node, defs_map)
        seen = seen | {ref}
    return node, seen


# ---------------------------------------------------------------------------
# Recursive emitter (inverse of _schema._element_to_schema)
# ---------------------------------------------------------------------------


def _emit_object_children(
    parent: etree._Element,
    obj_schema: dict[str, Any],
    defs_map: dict[str, Any],
    seen: frozenset[str],
) -> None:
    """Emit one child element per property of *obj_schema* under *parent*."""
    properties = obj_schema.get("properties")
    if not isinstance(properties, dict):
        return
    required = obj_schema.get("required")
    required_set = set(required) if isinstance(required, list) else set()

    for name, child_schema in properties.items():
        child = etree.SubElement(parent, name)
        _emit_schema(child, child_schema, defs_map, seen)
        if name not in required_set:
            child.set("required", "false")


def _emit_schema(
    element: etree._Element,
    schema: Any,
    defs_map: dict[str, Any],
    seen: frozenset[str],
) -> None:
    """Populate *element* (type + attributes + children) from *schema*."""
    if not isinstance(schema, dict):
        raise SchemaError(f"Schema fragment {schema!r} is not a schema object.")

    schema, seen = _inline(schema, defs_map, seen)

    # ── nullable shapes ──────────────────────────────────────────────────────
    inner, is_nullable = _unwrap_nullable(schema)
    if is_nullable:
        _emit_schema(element, inner, defs_map, seen)
        element.set("nullable", "true")
        return

    _reject_unions(schema)
    if "const" in schema:
        raise SchemaError(
            "'const' has no annotation-convention equivalent (the convention "
            "has no single-value constraint); cannot serialize it."
        )

    node_type = schema.get("type")

    # ── array ────────────────────────────────────────────────────────────────
    if node_type == "array":
        element.set("type", "array")
        _apply_scalar_attrs(element, schema)
        _apply_minmax(element, schema, is_array=True)
        _apply_enum(element, schema)
        item_tag = schema.get("x-weirding-item-tag")
        tag = item_tag if isinstance(item_tag, str) and item_tag else "item"
        items = schema.get("items")
        child = etree.SubElement(element, tag)
        _emit_schema(
            child, items if items is not None else {"type": "string"}, defs_map, seen
        )
        return

    # ── object ───────────────────────────────────────────────────────────────
    if node_type == "object" or "properties" in schema:
        element.set("type", "object")
        _apply_scalar_attrs(element, schema)
        _emit_object_children(element, schema, defs_map, seen)
        return

    # ── scalar leaf ──────────────────────────────────────────────────────────
    if isinstance(node_type, str):
        element.set("type", node_type)
    _apply_scalar_attrs(element, schema)
    _apply_minmax(element, schema, is_array=False)
    _apply_enum(element, schema)


# ---------------------------------------------------------------------------
# Attribute helpers (inverse of _schema._apply_attrs)
# ---------------------------------------------------------------------------


def _apply_scalar_attrs(element: etree._Element, schema: dict[str, Any]) -> None:
    """Emit the same-named string attributes (description/pattern/.../default)."""
    for key in _SCALAR_ATTRS:
        if key in schema:
            element.set(key, _stringify(schema[key]))


def _apply_minmax(
    element: etree._Element, schema: dict[str, Any], *, is_array: bool
) -> None:
    """Emit ``min``/``max`` from the type-appropriate length/item bounds."""
    min_key = "minItems" if is_array else "minLength"
    max_key = "maxItems" if is_array else "maxLength"
    if min_key in schema:
        element.set("min", _stringify(schema[min_key]))
    if max_key in schema:
        element.set("max", _stringify(schema[max_key]))


def _apply_enum(element: etree._Element, schema: dict[str, Any]) -> None:
    """Emit a pipe-joined ``enum`` attribute from a list of members."""
    enum = schema.get("enum")
    if isinstance(enum, list):
        element.set("enum", "|".join(_stringify(member) for member in enum))


def _stringify(value: Any) -> str:
    """Stringify a constraint value for an XML attribute.

    Booleans use lowercase XML form; everything else uses ``str``. Floats whose
    value is integral keep their ``.0`` (canonical IR stores ``minimum`` /
    ``maximum`` as ``float``; ``compile`` re-applies ``float()`` so the round
    trip is exact regardless).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Nullable + union handling
# ---------------------------------------------------------------------------


def _unwrap_nullable(schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Detect and unwrap the two accepted nullable shapes.

    Accepts ``{"anyOf": [T, {"type": "null"}]}`` (what ``_schema._wrap_nullable``
    emits) and ``{"type": [T, "null"], ...}`` (what ``to_json_schema(strict=True)``
    and some foreign IR emit). Returns ``(inner_schema, True)`` when nullable, or
    ``(schema, False)`` otherwise.
    """
    # Shape 1: 2-member anyOf with a null branch.
    members = schema.get("anyOf")
    if isinstance(members, list) and len(members) == 2:
        nulls = [m for m in members if _is_null_schema(m)]
        non_nulls = [m for m in members if not _is_null_schema(m)]
        if len(nulls) == 1 and len(non_nulls) == 1:
            inner = non_nulls[0]
            if isinstance(inner, dict):
                return inner, True

    # Shape 2: type-array containing "null".
    node_type = schema.get("type")
    if isinstance(node_type, list) and "null" in node_type:
        non_null_types = [t for t in node_type if t != "null"]
        if len(non_null_types) == 1:
            inner = {k: v for k, v in schema.items() if k != "type"}
            inner["type"] = non_null_types[0]
            return inner, True

    return schema, False


def _is_null_schema(member: Any) -> bool:
    """Return whether *member* is the ``{"type": "null"}`` null branch."""
    return isinstance(member, dict) and member.get("type") == "null"


def _reject_unions(schema: dict[str, Any]) -> None:
    """Raise on any non-null ``anyOf`` / ``oneOf`` / ``allOf``."""
    for combiner in ("anyOf", "oneOf", "allOf"):
        if combiner in schema:
            raise SchemaError(
                f"'{combiner}' has no annotation-convention representation (the "
                "convention has no union syntax beyond the nullable pattern); "
                "cannot serialize it to XML."
            )
