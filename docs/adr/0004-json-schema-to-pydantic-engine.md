# 0004: json-schema-to-pydantic as Model-Building Engine

**Status:** Accepted

**Date:** 2026-05-06

**Authors:** Ben Lin

## Context

`from_schema(schema: dict, *, name: str) -> type[BaseModel]` must convert a JSON Schema
IR dict into a live Pydantic v2 `BaseModel` class at runtime. This is a non-trivial
operation: it requires parsing JSON Schema keywords (`properties`, `required`, `$defs`,
`$ref`, `allOf`, `anyOf`, `enum`, `pattern`, constraints), resolving `$ref` pointers,
and constructing a Pydantic class with correct field types and validators — all without
invoking a code generator subprocess.

Two primary strategies were evaluated:

**`datamodel-code-generator` (banned):**
This library generates Python source code from JSON Schema, then executes or imports it.
It is the most feature-complete JSON Schema → Pydantic translator available, but it is
permanently banned as a runtime dependency (MEMORY.md rule 7). The reason: it invokes
`ruff` as a subprocess (50–200ms cold start) and `black` as a subprocess (800ms–2s cold
start). These latencies are unacceptable for a runtime library used in hot paths such as
Databricks ETL pipelines and Kubernetes request handlers where `from_schema()` may be
called on every request or record. It is also available as an optional `[codegen]` extra
for offline tooling use cases, but never importable at runtime.

**`json-schema-to-pydantic`:**
A pure-Python runtime library that converts JSON Schema dicts to Pydantic v2 `BaseModel`
classes without subprocess calls or code generation. It constructs field types using
Pydantic's internal metaclass machinery, resolving `$ref`, handling `$defs`, and mapping
common JSON Schema keywords to Pydantic equivalents. The library is available on PyPI as
`json-schema-to-pydantic>=0.4`.

**Writing a custom builder:**
A custom builder using `pydantic.create_model()` and `typing.get_type_hints()` was
considered. The implementation surface for handling all JSON Schema constructs correctly
(especially `$ref` cycles, `allOf` merging, `anyOf` discrimination, and `enum` types)
is substantial and would duplicate what `json-schema-to-pydantic` already does. The
maintenance burden outweighs the benefit of removing the dependency given that the
library's interface is stable.

Two gaps in `json-schema-to-pydantic` require weirding-owned patches applied after model
construction. These are deliberate extension points, not workarounds for bugs.

**Gap 1 — `additionalProperties: false` not enforced:**
The library recognizes `"additionalProperties": false` in the schema but does not set
`model_config = ConfigDict(extra="forbid")` on the generated model. Without this patch,
extra fields in the LLM's XML output are silently ignored rather than raising a
`ValidationError`. Silent acceptance of extra fields defeats the purpose of a strict
schema. weirding's `build_model()` inspects the schema and applies the patch
post-construction.

**Gap 2 — `prefixItems` not supported:**
`json-schema-to-pydantic` does not handle the `prefixItems` keyword (JSON Schema draft
2020-12 tuple validation). This is not a gap to patch around — it is a constraint that
informs the compiler. weirding's `compile()` / `_schema.py` is required to never emit
`prefixItems`. Positional sequences must be represented as named-field objects. This rule
is MEMORY.md rule 11.

**Maintainer risk:**
`json-schema-to-pydantic` is a single-maintainer library with moderate usage. If it
becomes unmaintained, the migration path is either: (a) pin the last working version and
maintain a fork, or (b) replace `build_model()` internals with `pydantic.create_model()`
calls, keeping the same external interface. The external interface of `from_schema()` and
`build_model()` is stable regardless of the engine, so callers are shielded from the
migration.

## Decision

`build_model(schema: dict, *, name: str = "Model") -> type[BaseModel]` in
`src/weirding/_models.py` uses `json-schema-to-pydantic>=0.4` as its engine, with two
weirding-owned post-construction patches.

`build_model()` is the implementation detail of `PydanticBuilder`, the default
`DTOBuilder` (see ADR-0002). `PydanticBuilder.build()` delegates to `build_model()`.
The `DTOBuilder` Protocol is the public abstraction; `build_model()` is the private
engine. This isolation means swapping `json-schema-to-pydantic` for another Pydantic
model builder leaves the `PydanticBuilder` interface — and all callers — unchanged.

**Patch 1:** After `build_model()` receives the generated class, if
`schema.get("additionalProperties") is False`, set `extra="forbid"` using the verified
Pydantic v2 post-construction API. The exact mechanism must be confirmed against Pydantic
v2 source before implementation — `model.__config_model__` does not exist. Candidate:
```python
model.model_config = ConfigDict(extra="forbid")
model.model_rebuild(force=True)
```
Evidence signal: a test that calls `model.model_validate({"known_field": "x", "extra": "y"})`
and asserts `ValidationError` is raised.

**Patch 2 (compile-time, not runtime):** `_schema.py` must never emit `prefixItems`.

`json-schema-to-pydantic` is added to `[project.dependencies]` in `pyproject.toml` as a
required runtime dependency (`json-schema-to-pydantic>=0.4`).

## Consequences

### Positive

- No subprocess calls. `from_schema()` is synchronous, has no process-spawn latency, and
  is safe to call in hot paths.
- `$defs`, `$ref`, `allOf`, `anyOf`, `enum`, `pattern`, `minimum`, `maximum`,
  `minLength`, `maxLength`, `minItems`, `maxItems` are handled by the library without
  custom code in weirding.
- The external API (`from_schema`, `build_model`) is engine-agnostic. Swapping the
  engine is a one-file change to `_models.py` with no callers affected.

### Negative

- Single-maintainer library. If development stops, weirding must fork or replace the
  engine. The `_models.py` isolation boundary makes this a contained migration, but it
  is real maintenance risk.
- `json-schema-to-pydantic` may lag behind JSON Schema draft evolution or Pydantic v2
  minor releases. weirding's CI must test against new Pydantic releases promptly.
- The two patches are weirding-owned code that must be tested independently. Any Pydantic
  v2 change to how `ConfigDict(extra="forbid")` is applied post-construction requires
  updating Patch 1.

### Neutral

- `datamodel-code-generator` remains available as an optional `[codegen]` extra for
  offline schema development tooling (e.g., generating typed stubs for a codebase). It
  must never be imported outside that extra.
- The `prefixItems` prohibition (rule 11) is a permanent architectural constraint on
  the IR compiler, not a temporary workaround. Even if `json-schema-to-pydantic` adds
  `prefixItems` support in a future release, weirding's IR will not emit it — positional
  sequences as named-field objects produce better Pydantic models and better LLM output.
