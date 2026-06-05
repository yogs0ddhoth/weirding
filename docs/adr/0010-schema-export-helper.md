# 0010: Schema-Export Helper (`to_json_schema`)

**Status:** Accepted

**Date:** 2026-06-05

**Authors:** Ben Lin

## Context

weirding's `compile(xml)` returns a public JSON Schema IR dict (ADR-0002), a draft
2020-12 schema carrying weirding-specific shapes: nullable fields as
`{"anyOf": [SCHEMA, {"type": "null"}]}`, an `x-weirding-item-tag` extension key on array
fields (ADR-0005), and — for the XSD dialect or caller-built input — local
`#/$defs/...` references which ADR-0002 declares part of the IR contract.

The library was positioned around Anthropic's XML-tag workflow, but the same IR is the
natural input to the structured-output features of the wider ecosystem: OpenAI / Azure
OpenAI Structured Outputs, Databricks `ai_query` `responseFormat`, and open-weight guided
decoding (vLLM, Ollama). Research across all four targets (2026-06-05) established that the
IR is **not accepted as-is** by the strict consumers, and that the *strip step* needed for
clean downstream use was already anticipated in the negative-consequences sections of
ADR-0002 and ADR-0005 ("may require a strip step in some pipelines"):

- **OpenAI / Azure strict mode** require `additionalProperties: false` on every object and
  every property listed in `required` (optional fields expressed as a null union); they
  reject `default` and forbid a `anyOf` root. They *accept* the collapsed `["T","null"]`
  nullable form and `$ref`/`$defs`.
- **Databricks `ai_query`** is the strictest consumer: it additionally forbids `anyOf`,
  `oneOf`, `allOf`, `pattern`, `prefixItems`, and `$ref`; permits nullable only as the
  collapsed `["T","null"]` list form; and caps a schema at 64 keys.
- **Open-weight backends** (vLLM `auto`/xgrammar, Ollama `format`) accept the IR
  essentially as-is, but the `x-weirding-*` extension keys add nothing to a decoding grammar
  and depend on "validators ignore unknown keywords" being true for every backend version.

The decision was whether to (a) leave this transform to each caller (docs-only), (b) add
per-provider helpers, or (c) add one provider-neutral helper. Option (a) pushes a
correctness-critical, fiddly transform onto users whose failure mode is an opaque provider
`400`. Option (b) multiplies surface for what is fundamentally one transform. The
non-obvious finding was that the OpenAI and Databricks requirements form a clean
**intersection**: a schema that collapses nullables to `["T","null"]`, inlines `$ref`,
forces `additionalProperties:false` + all-`required`, and strips the unsupported keywords
is valid for *both* — so a single strict mode covers them, and the non-strict mode covers
the permissive backends.

A separate, narrower question arose for the strict transform: how to handle `$ref`/`$defs`.
Databricks forbids `$ref` while ADR-0002 makes local refs contractual and OpenAI accepts
them — so the intersection is *narrower* than a keyword-strip list, and the helper must
actively inline (or reject) refs rather than pass them through.

## Decision

Add a public pure function `to_json_schema(ir: JsonSchemaIR, *, strict: bool = False) -> dict`,
implemented in a new unprotected module `src/weirding/_export.py` and exported from
`weirding.__init__` (`__all__`). It deep-copies its input, never mutates it, and performs
no I/O, logging, or network access.

- **`strict=False`** recursively strips every `x-weirding-*` extension key and leaves all
  standard JSON Schema keywords intact. This is the clean draft-2020-12 artifact for vLLM,
  Ollama, and `jsonschema`. It formalizes the strip step anticipated in ADR-0002/0005.

- **`strict=True`** produces the OpenAI ∩ Databricks intersection. On every object node it
  sets `additionalProperties: false` and sets `required` to the full list of property keys.
  Everywhere it collapses the 2-member nullable `anyOf` into `{"type": [T, "null"]}`,
  **inlines local `#/$defs/...` `$ref`s** (dropping the top-level `$defs`), and strips the
  unsupported-keyword set below. It **raises `SchemaError`** (the existing exception; no new
  type added) when the IR cannot be represented in the subset: a non-null-bearing
  `anyOf`/`oneOf`/`allOf`, a `$ref` that is non-local or unresolvable, a nullable
  (`anyOf`) root, a nullable branch whose non-null member has no `type` to collapse, or a
  transformed schema exceeding 64 total keys.

**Stripped keywords in strict mode** (`_STRIP_KEYWORDS`): `pattern`, `format`, `minimum`,
`maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minLength`, `maxLength`,
`minItems`, `maxItems`, `uniqueItems`, `default`, `patternProperties`, `propertyNames`,
`minProperties`, `maxProperties`.

**Conservative-strip note (binding on future maintainers):** `format`, `minimum`, and
`maximum` are stripped as a *conservative* choice — their support status in Databricks
`ai_query` is undocumented, not confirmed-unsupported. A future maintainer must **not**
"fix" this by re-adding them without first confirming Databricks acceptance; stripping is a
deliberate intersection decision, recorded in a comment at the `_STRIP_KEYWORDS` definition.

**64-key definition:** every key in every dict node of the transformed schema, summed
recursively across the whole document. This mirrors the total schema-key budget Databricks
enforces. Only the binding Databricks cap is enforced; OpenAI's far higher limits are not.

**Explicitly rejected:**
- *Docs-only* — pushes an error-prone transform onto users; opaque downstream `400`s.
- *Per-provider helpers* (`to_openai_schema`, `to_databricks_schema`, …) — the requirements
  intersect; one strict mode is sufficient and smaller surface.
- *Making `compile()` emit strict output* — the IR feeds `json-schema-to-pydantic`, which
  *uses* `minimum`/`pattern`/etc. to generate Pydantic `Field` constraints; stripping at
  compile time would degrade the primary Pydantic path and break the IR contract.
- *Building IR → Spark `StructType`* — out of scope; delegated to `sparkdantic` to avoid a
  PySpark dependency (MEMORY.md rule 6, binary-compat liability).

**Scope limitation:** this decision governs a transform *at the boundary*. `compile()`
output and the IR contract are unchanged. The helper reads the public IR and returns a
derived dict; it is not part of the IR itself.

## Consequences

### Positive

- One call (`to_json_schema(compile(xml), strict=True)`) yields a schema accepted unmodified
  by OpenAI, Azure, and Databricks `ai_query`; `strict=False` yields a clean schema for
  permissive open-weight backends.
- The fiddly, correctness-critical transform (which the OpenAI SDK performs internally via
  `to_strict_json_schema`) is owned and tested once, not re-invented per project.
- Pure, synchronous, dependency-free — consistent with the async and logging policies; safe
  to call on Spark executors.
- "Refuse rather than emit a rejected schema" (null root, forbidden combiners, oversized
  schema) converts opaque provider `400`s into actionable `SchemaError`s at the boundary.

### Negative

- Strict mode is **lossy by design**: it drops constraint keywords and rewrites optional
  properties to required-plus-null, changing what the model is constrained to produce.
  Documented in the docstring; callers who need those constraints enforced must do so
  outside the provider schema.
- A new public symbol is a forever-supported surface governed by the IR/semver policy.
- Inlining `$ref` expands schemas; combined with the 64-key cap, large XSD-derived schemas
  may raise in strict mode and require flattening by the caller.

### Neutral

- Adding `to_json_schema` to `__all__` is an additive change → semver **minor** (ADR-0002
  IR/format evolution policy; README format-stability contract).
- Future strict-subset adjustments (e.g. confirming Databricks `format` support, or a new
  provider widening/narrowing the intersection) require a new ADR — the strict keyword set
  and the `$ref`/64-key behavior are now a recorded contract, not an implementation detail.
