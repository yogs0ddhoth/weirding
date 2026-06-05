# 0011: Generated-Model Description Propagation

**Status:** Accepted

**Date:** 2026-06-05

**Authors:** Ben Lin

## Context

`build_model()` in `src/weirding/_models.py` (a Tier-2 protected file) produces the Pydantic
model returned by `from_schema()` / `define_model()`. After building the base model via
`json-schema-to-pydantic`, it re-subclasses to set the caller-supplied class name:

```python
named = type(name, (model,), {"__module__": model.__module__})
```

A class created with `type()` and no `"__doc__"` entry has `__doc__ == None` — `__doc__` is
**not** inherited from the base class. So every weirding-generated model has
`Model.__doc__ is None`, regardless of any `description` present in the source schema.

This is invisible in the XML/Pydantic round-trip path, but it degrades the ecosystem
integrations targeted in Phase 05. LangChain's `with_structured_output(Model)` and the
provider tool/function-calling paths derive the tool **description** from the model's schema
description, which Pydantic populates from the class docstring. With `__doc__ is None`, the
emitted tool/function has **no description** — which does not raise, but measurably reduces
tool-calling accuracy, most visibly on Anthropic (tool-calling default) and weaker
open-weight models. The weirding IR frequently carries a top-level `description` (authored in
the XML schema or derived from XSD annotations), so the information exists; it is simply
dropped at model-construction time.

Three options were considered:

- **Leave `__doc__` as `None`** — silently harms every LangChain/Anthropic user of a
  weirding model. Rejected.
- **Fix it in a `weirding[langchain]` adapter** — an adapter cannot set the description
  without re-wrapping the class (creating yet another subclass), and it would only fix the
  LangChain path, not the provider-native paths; it also couples weirding to `langchain-core`
  (rejected in the Phase 05 ideation as scope creep + a single-maintainer-cadence dependency,
  against the MEMORY.md pinning posture). Rejected.
- **Propagate the IR `description` into the generated class `__doc__`** at construction time —
  one key in the existing `type(...)` call; fixes every consumer at once. Chosen.

The change touches a Tier-2 protected file (`_models.py` — "changes risk silent model
generation regressions"), so it is recorded here with the alternatives and the regression
guard.

## Decision

In `build_model()`, when the source schema has a top-level `description`, include it as the
generated class's docstring:

```python
namespace = {"__module__": model.__module__}
description = schema.get("description")
if isinstance(description, str):
    namespace["__doc__"] = description
named = type(name, (model,), namespace)
```

When the schema has no `description`, behavior is unchanged (`__doc__` stays `None`). The
change is additive metadata only — it does not alter field definitions, types, validation, or
the `extra="forbid"` patch (ADR-0004 / MEMORY.md rule 12), which continues to apply
independently.

**Scope limitation:** only the top-level schema `description` populates `__doc__`. Per-field
descriptions already flow through `json-schema-to-pydantic` into `Field(description=...)` and
are unaffected by this decision.

## Consequences

### Positive

- `with_structured_output(Model)` and provider tool/function definitions now carry a real
  description, improving tool-calling accuracy across LangChain, Anthropic, OpenAI, and
  open-weight backends — fixed once, for every consumer, with no adapter and no new
  dependency.
- `Model.model_json_schema()["description"]` now reflects the authored schema description,
  making the generated model self-describing for any downstream JSON-Schema consumer.

### Negative

- A weirding-generated model's `__doc__` is now caller-influenced data (the schema
  description). Tooling that treats `__doc__` as developer-authored API documentation will
  see schema-supplied text. This is the intended behavior but is a small semantic shift.

### Neutral

- Adding an optional `__doc__` is additive → semver **minor**; no change to `compile()`
  output or the IR contract.
- A regression guard is required: the `extra="forbid"` patch and the XML round-trip tests
  must continue to pass after this change (verified in Phase 05). Future changes to
  `build_model()` remain governed by the Tier-2 protected-file rule.
