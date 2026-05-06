from pydantic import BaseModel


def build_model(schema: dict, *, name: str = "Model") -> type[BaseModel]:
    """Convert a JSON Schema IR dict to a Pydantic v2 BaseModel class.

    Engine: json-schema-to-pydantic.
    Patches applied here (not in the library):
      - schema["additionalProperties"] == False  →  model_config extra="forbid"
      - prefixItems must never appear in schema (enforced by _schema.py, not here)
    """
    raise NotImplementedError
