# 0002: JSON Schema IR as Public API

**Status:** Accepted

**Date:** 2026-05-06

**Authors:** Ben Lin

## Context

weirding's core operation is: XML schema document → intermediate representation → Pydantic
model. The intermediate representation (IR) is a JSON Schema-compatible dict (draft
2020-12 subset). The question is whether this dict is an internal implementation detail
or a first-class public API surface.

The initial design treated the IR as internal: callers would use `define_model(xml)` and
get a Pydantic model back. The IR would be an in-process dict that callers never saw.

This became untenable when weirding's deployment targets were examined in full:

**Databricks / Apache Spark:** Databricks users building AI-aided ETL pipelines need
typed schemas to define DataFrame columns, register `StructType` schemas, and validate
ingested data. Databricks provides `pyspark.sql.functions.from_json()` with a
`StructType` schema argument — but there is no Pydantic involved. A Databricks user
calling `define_model()` to get a Pydantic class only to immediately discard it and
call `.schema()` to get the JSON Schema back again is an absurd round-trip. The user
needs the JSON Schema dict directly.

**OpenAPI specification generation:** Systems that consume weirding output to populate
OpenAPI specs need the JSON Schema dict as input to `openapi-pydantic`,
`spectree`, or similar tools. These libraries accept JSON Schema dicts natively.

**jsonschema validation:** `jsonschema.validate(instance, schema)` accepts a dict.
A caller who wants to validate without Pydantic (e.g., in a serverless function without
Pydantic installed) is unnecessarily blocked if the dict is internal.

**Custom model builders:** Callers in edge environments (Lambda, Cloudflare Workers via
Python, embedded runtimes) may want to use a lighter validation library such as
`cattrs`, `msgspec`, or a custom TypedDict-based approach. Locking them into Pydantic
as the only consumer of the IR imposes an unnecessary dependency.

The counter-argument for keeping IR internal is API surface stability: exposing the dict
means weirding must maintain its structure as a public contract. Changes to the IR format
become breaking changes. This is a real cost, but it is lower than the cost of forcing
every non-Pydantic consumer through an undocumented workaround.

## Decision

`compile(xml: str | bytes) -> dict` is a **public, documented, stable API entry point**.
The JSON Schema IR dict it returns is a public contract following JSON Schema draft 2020-12.

`from_schema(schema: dict, *, name: str = "Model", builder: DTOBuilder | None = None) -> type`
is also public. With the default builder (`PydanticBuilder`), it returns `type[BaseModel]`
and is overloaded accordingly for static type checkers. Passing a custom `DTOBuilder`
allows callers to produce TypedDicts, dataclasses, Spark StructType wrappers, or any
typed DTO from the same JSON Schema IR dict.

The `DTOBuilder` Protocol is defined in `weirding.__init__` and exported:
```python
@runtime_checkable
class DTOBuilder(Protocol):
    def build(self, schema: dict, *, name: str) -> type: ...
```

`PydanticBuilder` (defined in `_models.py`, exported from `weirding.__init__`) is the
default implementation. It wraps `json-schema-to-pydantic` with the two weirding-owned
patches (see ADR-0004). Callers who want Pydantic behavior can import and subclass it.

The IR structure follows JSON Schema draft 2020-12 with the following weirding-specific
restrictions, which are part of the public contract:
- `prefixItems` is never emitted (positional sequences are named-field objects).
- `$schema` is not emitted in the top-level dict (callers who need it may add it).
- All `$ref` URIs are local (`#/$defs/...`) — no network URIs.
- Array fields carry a `x-weirding-item-tag` extension key naming the child element
  (see ADR-0005). This key is part of the IR contract and is preserved through
  `from_schema()` into model metadata for use by `to_xml()`.

All three functions — `compile`, `from_schema`, `DTOBuilder`, `PydanticBuilder` — are
listed in `__all__` in `weirding.__init__`.

`define_model(xml, *, builder=None)` remains as a convenience wrapper:
```python
schema = compile(xml)
return from_schema(schema, name=<sanitized root tag>, builder=builder)
```

It is a one-call shortcut; the builder parameter threads through.

## Consequences

### Positive

- Databricks, Spark, and jsonschema users can use `compile()` directly without a Pydantic
  dependency or an undocumented internal import.
- `from_schema()` with `DTOBuilder` Protocol enables any typed DTO — TypedDict, dataclass,
  Spark StructType wrapper, Pydantic model — to be built from the same JSON Schema IR
  without changing the public API signature or the IR contract.
- The `Validatable` Protocol on `parse()` and the `DTOBuilder` Protocol on `from_schema()`
  are symmetric: both ends of the pipeline are backend-neutral. Pydantic is the default
  implementation, not the required implementation.
- Callers who want to cache, serialize, version, or inspect the schema before building a
  model can do so without monkey-patching internals.
- The JSON Schema dict is directly usable as an OpenAPI component schema, a Databricks
  `StructType` converter input, or a `jsonschema.validate()` argument.

### Negative

- The IR structure is now a versioned public contract. Changes to how `compile()` represents
  nullables, enums, `$defs`, or `allOf` are potentially breaking. Any such change requires
  a semver major bump and a deprecation path.
- Callers who build on the raw dict may depend on structure that weirding considers
  implementation detail (e.g., exact `$defs` key names). This is inherent to exposing the
  dict; documentation must clearly state which parts of the structure are stable.

### Neutral

- The weirding-specific restrictions (no `prefixItems`, no network `$ref`, no `$schema`
  emission) must be documented at the `compile()` docstring level so callers know exactly
  what subset they receive.
- Future dialect compilers (XSD in Phase 03) must emit the same IR shape with the same
  restrictions. The IR spec is dialect-agnostic.
