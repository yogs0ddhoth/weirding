"""Neutral local ``$ref`` resolution core, shared by reverse-edge emitters.

This module holds the *resolution logic only* — looking up a local
``#/$defs/NAME`` reference against a defs map and merging sibling keywords —
with neutral, caller-agnostic error wording. Consumers that need
domain-specific phrasing (e.g. :mod:`weirding._export`'s strict-mode messages)
wrap these helpers and translate the error text. Keeping one resolution core
means ``_export`` (forward, IR → provider schema) and ``_decompile`` (reverse,
IR → XML) cannot drift in how they inline references. See ADR-0012.
"""

from __future__ import annotations

import copy
from typing import Any

from weirding._exceptions import SchemaError

_LOCAL_PREFIX = "#/$defs/"


def lookup_def(ref: str, defs_map: dict[str, Any]) -> Any:
    """Look up a local ``#/$defs/NAME`` reference against *defs_map*.

    Args:
        ref: The ``$ref`` string to resolve.
        defs_map: The document's ``$defs`` mapping (name → schema).

    Returns:
        The referenced schema object (not copied).

    Raises:
        SchemaError: The ref is not a local ``#/$defs/...`` reference, or it
            names a definition absent from *defs_map*. The message names *ref*.
    """
    if not ref.startswith(_LOCAL_PREFIX):
        raise SchemaError(
            f"$ref {ref!r} is not a local '#/$defs/...' reference; only local "
            "references can be inlined."
        )
    name = ref[len(_LOCAL_PREFIX) :]
    if name not in defs_map:
        raise SchemaError(
            f"$ref {ref!r} cannot be resolved against the document's '$defs'."
        )
    return defs_map[name]


def resolve_ref(node: dict[str, Any], defs_map: dict[str, Any]) -> dict[str, Any]:
    """Inline a local ``$ref`` in *node* and merge its sibling keywords.

    Args:
        node: A schema dict containing a ``$ref`` key.
        defs_map: The document's ``$defs`` mapping.

    Returns:
        A new dict: a deep copy of the referenced target with *node*'s sibling
        keywords merged in (the target's own keys win on conflict).

    Raises:
        SchemaError: The ref cannot be resolved, or its target is not a schema
            object. The message names the offending ``$ref``.
    """
    ref = node["$ref"]
    target = lookup_def(ref, defs_map)
    merged = copy.deepcopy(target)
    if not isinstance(merged, dict):
        raise SchemaError(f"$ref target {ref!r} is not a schema object.")
    for key, value in node.items():
        if key == "$ref":
            continue
        merged.setdefault(key, value)
    return merged
