# 0003: Validatable Protocol for parse()

**Status:** Accepted

**Date:** 2026-05-06

**Authors:** Ben Lin

## Context

`parse(xml, model)` deserializes an LLM-produced XML document into a typed Python object.
The question is what type constraint to place on `model`.

The obvious choice is `type[BaseModel]` — every model produced by `define_model()` or
`from_schema()` is a `BaseModel` subclass, so this is always satisfied. The problem is
what this forecloses.

weirding targets Databricks AI pipelines and Kubernetes-hosted services alongside
standard Python environments. These environments have meaningfully different validation
libraries and constraints:

**Databricks:** Pydantic is available but `pyspark.sql.types.StructType` is the native
schema type. Data scientists building ETL pipelines that ingest XML may want to validate
with a lighter `TypedDict`-based approach or use `msgspec` for throughput reasons.
Requiring Pydantic BaseModel as a hard type constraint forces a dependency that may not
be appropriate.

**Serverless / edge:** Lambda and similar runtimes have cold-start costs sensitive to
import time. Pydantic v2 with Rust extensions is fast to execute but adds package size.
Some edge deployments may want to validate against a simpler schema checker.

**Testing and mocking:** Unit tests that don't want to construct a full Pydantic model
class for a narrow test can pass a duck-typed validator. A hard `BaseModel` constraint
prevents this.

The standard Python solution for this kind of structural flexibility is a `Protocol`.
A Protocol defines the interface that satisfies the constraint without requiring
inheritance from a specific class. This is the `@runtime_checkable` Protocol pattern
from PEP 544.

The minimal interface `parse()` requires from its `model` argument is one classmethod:
`model_validate(cls, obj: dict[str, Any]) -> Any`. Every Pydantic v2 `BaseModel`
subclass satisfies this without any changes. Non-Pydantic validators that implement
this single method also satisfy it.

The alternative is to accept `Any` and add a runtime duck-type check (which is
effectively what `@runtime_checkable` Protocol provides, but without the type system
benefit). This is strictly worse: it provides no type-checker signal to callers.

## Decision

`parse(xml: str | bytes, model: type[Validatable]) -> Any` accepts any type satisfying
the `Validatable` protocol, not a concrete `type[BaseModel]`.

`Validatable` is defined as:

```python
@runtime_checkable
class Validatable(Protocol):
    @classmethod
    def model_validate(cls, obj: dict[str, Any]) -> Any: ...
```

`Validatable` is exported from `weirding.__init__` and is part of the public API. Callers
who build custom validators can import it to check conformance.

Every Pydantic v2 `BaseModel` subclass satisfies `Validatable` without modification.
No changes to the Pydantic-based workflow are required.

The method name `model_validate` was chosen because:
1. It is the exact method name Pydantic v2 uses — zero adaptation required for the
   primary use case.
2. It signals "this is a structured validation entry point" which is consistent with how
   Pydantic names its API (`model_validate`, `model_dump`, `model_json_schema`).
3. Non-Pydantic validators implementing this protocol advertise Pydantic API compatibility,
   which is a reasonable expectation for libraries targeting weirding integration.

## Consequences

### Positive

- Non-Pydantic validators (TypeAdapter wrappers, msgspec, cattrs adapters, mock
  validators in tests) can be used with `parse()` without any weirding changes.
- The public API signature does not need to change when a new backend is added.
  Adding Spark StructType validation support would be a new adapter class, not an
  API revision.
- Type checkers (mypy, pyright) correctly flag callers that pass an incompatible type to
  `parse()`, since `@runtime_checkable` Protocol supports static analysis.

### Negative

- The return type of `parse()` is `Any`. This is unavoidable without making the function
  generic (`parse[T](xml, model: type[Validatable[T]]) -> T`). A generic version is
  possible but adds complexity; callers can add their own type narrowing if needed.
- The Protocol method name `model_validate` embeds a Pydantic naming convention. A
  validator library that uses a different name (e.g., `validate`, `from_dict`) must wrap
  itself in an adapter. This is a one-method adapter, but it is extra surface area.

### Neutral

- The `@runtime_checkable` decorator enables `isinstance(model, Validatable)` checks
  at runtime, which weirding's `parse()` uses to provide a clear error message when
  a caller passes an incompatible type.
- Future typed variants (`parse[T]`) can be added as overloads without breaking the
  existing signature.
