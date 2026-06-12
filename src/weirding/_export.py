"""Transform the public JSON Schema IR into provider-ready JSON Schema documents.

This module formalizes the extension-key strip step anticipated in the negative
consequences of ADR-0002 and ADR-0005, and adds a strict variant accepted
unmodified by the OpenAI / Azure Structured Outputs and Databricks ``ai_query``
``responseFormat`` intersection.

The single entry point is :func:`to_json_schema`. It is a pure function: it
deep-copies its input, never mutates the input dict, and performs no I/O,
logging, or network access.
"""

from __future__ import annotations

import copy
from typing import Any

from weirding import _refs
from weirding._exceptions import SchemaError
from weirding._types import JsonSchemaIR

# JSON Schema keywords stripped in strict mode. These are either unsupported by
# Databricks ``ai_query`` (the strictest consumer) or are a conservative removal
# because their support status there is undocumented. A future maintainer should
# NOT re-add these without confirming Databricks support — stripping them is a
# deliberate intersection choice, not an oversight (see ADR-0010).
_STRIP_KEYWORDS: frozenset[str] = frozenset(
    {
        "pattern",
        "format",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
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
)

# Databricks ``ai_query`` caps a ``responseFormat`` schema at 64 keys.
_MAX_STRICT_KEYS = 64


def to_json_schema(ir: JsonSchemaIR, *, strict: bool = False) -> dict[str, Any]:
    """Transform a weirding JSON Schema IR into a provider-ready schema.

    The input is the public ``JsonSchemaIR`` dict returned by
    :func:`weirding.compile`. The function never mutates its input; it operates
    on a deep copy and returns a new dict.

    Args:
        ir: A JSON Schema IR dict (as produced by :func:`weirding.compile` or any
            compatible source).
        strict: When ``False`` (default), produce clean JSON Schema draft 2020-12
            by recursively stripping every ``x-weirding-*`` extension key while
            leaving all standard JSON Schema keywords intact. Suitable for
            permissive backends (vLLM, Ollama, ``jsonschema``).

            When ``True``, produce the OpenAI ∩ Databricks intersection schema.
            Recursively, on every object node, ``additionalProperties`` is set to
            ``False`` and ``required`` is set to the full list of property keys
            (every optional property is promoted to required). Everywhere, the
            2-member nullable pattern ``{"anyOf": [SCHEMA, {"type": "null"}]}``
            that weirding emits is collapsed into ``{"type": [T, "null"], ...}``,
            local ``$ref`` / ``$defs`` are inlined, and unsupported keywords are
            stripped.

    Returns:
        A new JSON Schema dict. In strict mode the result contains no ``$defs``,
        no ``$ref``, no ``anyOf`` / ``oneOf`` / ``allOf``, no ``x-weirding-*``
        keys, and none of the stripped constraint keywords.

    Raises:
        SchemaError: In strict mode, raised when the IR cannot be represented in
            the intersection subset. The message names the offending construct.
            This happens when: a non-null-bearing ``anyOf`` / ``oneOf`` /
            ``allOf`` is present (Databricks forbids them); a local ``$ref``
            cannot be resolved against the document's ``$defs``; the root would be
            a null-wrapped ``anyOf`` (a nullable root); or the transformed schema
            exceeds the Databricks 64-key cap.

    Note:
        Strict mode is lossy by design. It drops constraint keywords (``pattern``,
        ``minimum``, ``maximum``, ``format``, length / item bounds, ``default``,
        and others) and changes optional properties to required. The set of
        stripped keywords is the conservative Databricks intersection, not a
        docs-mandated removal list.

        Key-count definition for the 64-key cap: every key in every dict node of
        the transformed schema is counted, summed across the whole document
        (the top-level dict plus all nested ``properties`` values, ``items``,
        and ``type``-array members). This mirrors the total schema-key budget
        Databricks ``ai_query`` enforces.
    """
    document = copy.deepcopy(ir)

    if not strict:
        return _strip_extensions(document)

    defs = document.get("$defs")
    defs_map: dict[str, Any] = defs if isinstance(defs, dict) else {}

    if _is_nullable_anyof(document):
        raise SchemaError(
            "Cannot export a nullable root schema in strict mode: the root is a "
            "null-wrapped 'anyOf', which OpenAI and Databricks reject. Make the "
            "root object non-nullable before exporting."
        )

    result = _strictify(document, defs_map)
    result.pop("$defs", None)

    key_count = _count_keys(result)
    if key_count > _MAX_STRICT_KEYS:
        raise SchemaError(
            f"Strict schema has {key_count} keys, exceeding the Databricks "
            f"ai_query cap of {_MAX_STRICT_KEYS}. Reduce the schema size "
            "(fewer fields or shallower nesting) before exporting."
        )

    return result


# ---------------------------------------------------------------------------
# Non-strict: extension-key stripping
# ---------------------------------------------------------------------------


def _strip_extensions(node: Any) -> Any:
    """Recursively remove every ``x-weirding-*`` key, leaving everything else."""
    if isinstance(node, dict):
        return {
            key: _strip_extensions(value)
            for key, value in node.items()
            if not _is_extension_key(key)
        }
    if isinstance(node, list):
        return [_strip_extensions(item) for item in node]
    return node


# ---------------------------------------------------------------------------
# Strict: OpenAI ∩ Databricks intersection
# ---------------------------------------------------------------------------


def _strictify(node: dict[str, Any], defs_map: dict[str, Any]) -> dict[str, Any]:
    """Transform a single schema node into the strict intersection subset.

    The node is assumed not to be a top-level nullable ``anyOf`` root (that case
    is rejected by the caller). Nested nullable ``anyOf`` patterns are collapsed
    in place.
    """
    # Resolve a bare local ref first so the rest of the logic sees a real schema.
    if "$ref" in node:
        node = _resolve_ref(node, defs_map)

    if _is_nullable_anyof(node):
        return _collapse_nullable(node, defs_map)

    for combiner in ("anyOf", "oneOf", "allOf"):
        if combiner in node:
            raise SchemaError(
                f"Cannot export schema in strict mode: '{combiner}' is not "
                "supported by Databricks ai_query and the OpenAI ∩ Databricks "
                "intersection cannot represent it. Only the 2-member nullable "
                "pattern (anyOf with a null branch) is allowed."
            )

    result: dict[str, Any] = {}
    for key, value in node.items():
        if _is_extension_key(key) or key in _STRIP_KEYWORDS or key == "$defs":
            continue
        result[key] = value

    if "properties" in result and isinstance(result["properties"], dict):
        result["properties"] = {
            name: _strictify_child(child, defs_map)
            for name, child in result["properties"].items()
        }

    if "items" in result and isinstance(result["items"], dict):
        result["items"] = _strictify_child(result["items"], defs_map)

    if result.get("type") == "object" or "properties" in result:
        props = result.get("properties")
        prop_names = list(props.keys()) if isinstance(props, dict) else []
        result["additionalProperties"] = False
        result["required"] = prop_names

    return result


def _strictify_child(child: Any, defs_map: dict[str, Any]) -> Any:
    """Apply :func:`_strictify` to a child value that should be a schema dict."""
    if isinstance(child, dict):
        return _strictify(child, defs_map)
    return child


def _collapse_nullable(
    node: dict[str, Any], defs_map: dict[str, Any]
) -> dict[str, Any]:
    """Collapse a 2-member nullable ``anyOf`` into a ``type``-array schema.

    ``{"anyOf": [SCHEMA, {"type": "null"}], ...}`` becomes
    ``{"type": [T, "null"], ...}`` with SCHEMA's keywords merged in, where ``T``
    is SCHEMA's ``type``. Any sibling keywords on the wrapper are preserved.
    """
    members = node["anyOf"]
    non_null = next(m for m in members if not _is_null_schema(m))

    resolved = non_null
    if isinstance(resolved, dict) and "$ref" in resolved:
        resolved = _resolve_ref(resolved, defs_map)

    inner = _strictify(resolved, defs_map)

    inner_type = inner.get("type")
    if isinstance(inner_type, list):
        if "null" not in inner_type:
            inner_type = [*inner_type, "null"]
    elif inner_type is None:
        raise SchemaError(
            "Cannot export schema in strict mode: a nullable branch has no "
            "'type' keyword, so it cannot be collapsed into a type-array. "
            "Give the non-null branch an explicit type."
        )
    else:
        inner_type = [inner_type, "null"]
    inner["type"] = inner_type

    # Merge any sibling keywords from the wrapper (other than the anyOf itself).
    for key, value in node.items():
        if key == "anyOf" or _is_extension_key(key) or key in _STRIP_KEYWORDS:
            continue
        inner.setdefault(key, value)

    return inner


def _resolve_ref(node: dict[str, Any], defs_map: dict[str, Any]) -> dict[str, Any]:
    """Inline a local ``$ref`` against ``defs_map`` and merge sibling keywords.

    Wraps the neutral :func:`weirding._refs.resolve_ref` core, translating its
    neutral errors into the strict-mode message wording this module's callers
    (and tests) expect.
    """
    ref = node["$ref"]
    try:
        return _refs.resolve_ref(node, defs_map)
    except SchemaError as exc:
        raise SchemaError(_strict_ref_message(ref, defs_map)) from exc


def _lookup_def(ref: str, defs_map: dict[str, Any]) -> Any:
    """Look up a local ``#/$defs/NAME`` reference, raising if unresolvable.

    Wraps the neutral :func:`weirding._refs.lookup_def` core, translating its
    neutral errors into the strict-mode message wording.
    """
    try:
        return _refs.lookup_def(ref, defs_map)
    except SchemaError as exc:
        raise SchemaError(_strict_ref_message(ref, defs_map)) from exc


def _strict_ref_message(ref: str, defs_map: dict[str, Any]) -> str:
    """Return the strict-mode error text for an unusable ``$ref``."""
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return (
            f"Cannot export schema in strict mode: '$ref' {ref!r} is not a local "
            "'#/$defs/...' reference. Databricks forbids '$ref'; only inlinable "
            "local references are supported."
        )
    name = ref[len(prefix) :]
    if name not in defs_map:
        return (
            f"Cannot export schema in strict mode: '$ref' {ref!r} cannot be "
            "resolved against the document's '$defs'."
        )
    return (
        f"Cannot export schema in strict mode: '$ref' target {ref!r} is not "
        "a schema object."
    )


# ---------------------------------------------------------------------------
# Predicates and counting
# ---------------------------------------------------------------------------


def _is_extension_key(key: Any) -> bool:
    """Return whether *key* is a weirding ``x-weirding-*`` extension key."""
    return isinstance(key, str) and key.startswith("x-weirding-")


def _is_null_schema(member: Any) -> bool:
    """Return whether *member* is the ``{"type": "null"}`` null branch."""
    return isinstance(member, dict) and member.get("type") == "null"


def _is_nullable_anyof(node: Any) -> bool:
    """Return whether *node* is the 2-member nullable ``anyOf`` weirding emits."""
    if not isinstance(node, dict):
        return False
    members = node.get("anyOf")
    if not isinstance(members, list) or len(members) != 2:
        return False
    return any(_is_null_schema(m) for m in members) and not all(
        _is_null_schema(m) for m in members
    )


def _count_keys(node: Any) -> int:
    """Count every dict key in *node*, summed recursively across the document."""
    total = 0
    if isinstance(node, dict):
        total += len(node)
        for value in node.values():
            total += _count_keys(value)
    elif isinstance(node, list):
        for item in node:
            total += _count_keys(item)
    return total
