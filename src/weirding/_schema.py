def compile_schema(xml: str | bytes) -> dict:
    """Parse an XML schema document (data-* convention) into a JSON Schema IR dict.

    Never emits prefixItems — positional sequences are represented as named-field
    objects. See MEMORY.md rule 11.
    """
    raise NotImplementedError
