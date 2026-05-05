from __future__ import annotations

from pydantic import BaseModel

from weirding._exceptions import (
    ParseError,
    SchemaError,
    UnsupportedDialectError,
    WeirdingError,
)

__all__ = [
    "ParseError",
    "SchemaError",
    "UnsupportedDialectError",
    "WeirdingError",
    "define_model",
    "parse",
    "to_xml",
]


def define_model(xml: str | bytes) -> type[BaseModel]:
    raise NotImplementedError


def parse(xml: str | bytes, model: type[BaseModel]) -> BaseModel:
    raise NotImplementedError


def to_xml(instance: BaseModel) -> str:
    raise NotImplementedError
