from __future__ import annotations

import types as _types
from typing import TYPE_CHECKING, Literal, Union, get_args, get_origin

from lxml import etree
from pydantic import BaseModel
from pydantic import ValidationError as _PydanticValidationError
from pydantic.fields import FieldInfo

from weirding._exceptions import ParseError
from weirding._serializers import _item_tag_for_field

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Optional / nullable helpers
# ---------------------------------------------------------------------------


def _is_optional(ann: object) -> bool:
    """Return True if *ann* is ``X | None`` (3.10+ syntax) or ``Optional[X]``."""
    return isinstance(ann, _types.UnionType) or (
        get_origin(ann) is Union and type(None) in get_args(ann)
    )


def _unwrap_optional(ann: object) -> object:
    """Return the non-None type inside an Optional annotation."""
    return next(a for a in get_args(ann) if a is not type(None))


# ---------------------------------------------------------------------------
# Scalar type name map
# ---------------------------------------------------------------------------

_SCALAR_TYPE_NAMES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
}


# ---------------------------------------------------------------------------
# Recursive rendering helpers
# ---------------------------------------------------------------------------


def _render_scalar_or_object(elem: etree._Element, ann: object) -> None:
    """Populate a list-item element with its placeholder text or child fields."""
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        _render_model_fields(elem, ann)
    elif ann is bool:
        elem.text = "true"
    else:
        elem.text = _SCALAR_TYPE_NAMES.get(ann, "string")  # type: ignore[arg-type]


def _render_model_fields(parent: etree._Element, model: type[BaseModel]) -> None:
    """Append field elements for all fields in *model* to *parent*."""
    for field_name, field_info in model.model_fields.items():
        _render_field(parent, field_name, field_info)


def _render_field(
    parent: etree._Element, field_name: str, field_info: FieldInfo
) -> None:
    """Append annotation comments + field element to *parent*."""
    ann = field_info.annotation
    optional = False

    if ann is not None and _is_optional(ann):
        optional = True
        ann = _unwrap_optional(ann)

    # Description comment — appears before optional marker
    if field_info.description:
        parent.append(etree.Comment(f" {field_info.description} "))

    # Optional marker
    if optional:
        parent.append(etree.Comment(" optional "))

    # List field
    if get_origin(ann) is list:
        item_args = get_args(ann)
        item_type = item_args[0] if item_args else str
        item_tag = _item_tag_for_field(field_name, field_info)
        wrapper = etree.SubElement(parent, field_name)
        for _ in range(2):
            child = etree.SubElement(wrapper, item_tag)
            _render_scalar_or_object(child, item_type)
        wrapper.append(etree.Comment(" repeat as needed "))
        return

    # Nested object field
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        elem = etree.SubElement(parent, field_name)
        _render_model_fields(elem, ann)
        return

    # Enum (Literal) field
    if get_origin(ann) is Literal:
        values = " | ".join(str(v) for v in get_args(ann))
        parent.append(etree.Comment(f" allowed values: {values} "))
        elem = etree.SubElement(parent, field_name)
        elem.text = "string"
        return

    # Boolean — special case: use "true" not "boolean"
    if ann is bool:
        elem = etree.SubElement(parent, field_name)
        elem.text = "true"
        return

    # Other scalars
    elem = etree.SubElement(parent, field_name)
    elem.text = _SCALAR_TYPE_NAMES.get(ann, "string")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class RetryContext:
    """Stateful context for an LLM structured-output retry loop.

    Tracks attempt count and accumulated errors so that format_error()
    can produce increasingly specific retry prompts without the caller
    managing state.
    """

    def __init__(self, model: type[BaseModel], max_attempts: int = 3) -> None:
        self._model = model
        self._max_attempts = max_attempts
        self._attempt = 0
        self._last_message: str | None = None

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def exceeded(self) -> bool:
        return self._attempt >= self._max_attempts

    def record_error(self, error: Exception) -> None:
        self._attempt += 1
        self._last_message = format_error(error, model=self._model)

    def retry_message(self) -> str:
        return self._last_message or ""


def to_template(model: type[BaseModel]) -> str:
    """Generate an XML prompt template from a compiled Pydantic model.

    Produces an XML document showing the expected element structure and
    field types, suitable for inclusion in an LLM system prompt. Scalar
    fields are rendered as <field>{type}</field>; objects as nested elements.

    Args:
        model: A type[BaseModel] produced by define_model() or from_schema().

    Returns:
        XML string showing the expected output format.
    """
    root = etree.Element(model.__name__)
    _render_model_fields(root, model)
    return etree.tostring(root, encoding="unicode", pretty_print=True)


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    """Convert a Pydantic v2 ``loc`` tuple to dot-bracket notation.

    Examples::

        ("items", 0, "name") → "items[0].name"
        ("status",)          → "status"
        ()                   → ""
        ("__root__",)        → ""   # root-validator artifact; not useful in retry
    """
    parts: list[str] = []
    for part in loc:
        if part == "__root__":
            continue
        if isinstance(part, int):
            if parts:
                parts[-1] = parts[-1] + f"[{part}]"
            else:
                parts.append(f"[{part}]")
        else:
            parts.append(str(part))
    return ".".join(parts)


def format_error(error: Exception, *, model: type[BaseModel]) -> str:
    """Format a validation error into a natural-language retry instruction.

    Converts pydantic.ValidationError (or weirding.ParseError wrapping one)
    into a human-readable description of what the LLM got wrong, suitable
    for appending to a retry prompt.

    Args:
        error: The exception raised by parse() on the failed attempt.
        model: The model that was being validated against. Used to provide
               field-level context in the error message.

    Returns:
        Plain text description of the validation failures.
    """
    # Unwrap ParseError — weirding raises ParseError(str(exc)) from exc
    if isinstance(error, ParseError) and isinstance(
        error.__cause__, _PydanticValidationError
    ):
        ve = error.__cause__
    elif isinstance(error, _PydanticValidationError):
        ve = error
    else:
        return f"Unexpected error: {error}"

    lines = []
    for err in ve.errors(include_url=False, include_input=False, include_context=True):
        # PRIVACY: include_input=False is MANDATORY.
        # LLM output may contain user-submitted PII. Never echo input values
        # into retry messages — this violates CLAUDE.md privacy requirements.
        # Any future include_values=True opt-in requires explicit privacy review.
        path = _loc_to_path(err["loc"])
        msg = err["msg"]
        lines.append(f"  - {path}: {msg}" if path else f"  - {msg}")

    count = ve.error_count()
    noun = "error" if count == 1 else "errors"
    return f"The previous response had {count} validation {noun}:\n" + "\n".join(lines)
