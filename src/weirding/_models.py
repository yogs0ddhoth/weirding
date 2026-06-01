from json_schema_to_pydantic import create_model
from json_schema_to_pydantic.exceptions import CombinerError, ReferenceError
from json_schema_to_pydantic.exceptions import SchemaError as LibSchemaError
from json_schema_to_pydantic.exceptions import TypeError as LibTypeError
from pydantic import BaseModel, ConfigDict

from weirding._exceptions import SchemaError
from weirding._types import JsonSchemaIR


def build_model(schema: JsonSchemaIR, *, name: str = "Model") -> type[BaseModel]:
    """Convert a JSON Schema IR dict to a Pydantic v2 BaseModel class.

    Engine: json-schema-to-pydantic.
    Patches applied here (not in the library):
      - schema["additionalProperties"] == False  →  model_config extra="forbid"
      - prefixItems must never appear in schema (enforced by _schema.py, not here)
    """

    try:
        model = create_model(schema)
    except (LibSchemaError, LibTypeError, CombinerError, ReferenceError) as exc:
        raise SchemaError(str(exc)) from exc

    # Patch 1: additionalProperties: false → extra="forbid"
    if schema.get("additionalProperties") is False:
        model.model_config = ConfigDict(extra="forbid")
        model.model_rebuild(force=True)

    # Set the class __name__ to the caller-supplied name
    named = type(name, (model,), {"__module__": model.__module__})
    named.model_rebuild(force=True)
    return named
