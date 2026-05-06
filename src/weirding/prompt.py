from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel


class RetryContext:
    """Stateful context for an LLM structured-output retry loop.

    Tracks attempt count and accumulated errors so that format_error()
    can produce increasingly specific retry prompts without the caller
    managing state.
    """

    def __init__(self, model: type[BaseModel]) -> None:
        raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError
