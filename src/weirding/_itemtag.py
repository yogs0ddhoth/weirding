"""Shared singularization fallback for XML array item tags.

The fallback heuristic lives here, in one place, so that the two call sites that
need it — ``_serializers._item_tag_for_field`` (forward, model → XML) and
``_introspect.to_schema`` (reverse, model → IR) — cannot drift. See ADR-0012.
"""

from __future__ import annotations


def item_tag_fallback(field_name: str) -> str:
    """Return a synthesized XML child tag for the items of *field_name*.

    Used only when no ``x-weirding-item-tag`` is present. Strips a trailing
    ``s`` from a plural field name (e.g. ``tags`` → ``tag``); falls back to the
    literal ``"item"`` when the field name has no trailing ``s`` to strip.

    Args:
        field_name: The name of the array-typed field.

    Returns:
        The singularized field name, or ``"item"`` when no singular form
        applies.
    """
    if field_name.endswith("s") and len(field_name) > 1:
        return field_name[:-1]
    return "item"
