# 0012: Reverse-Edge Functions — Closing the XML ↔ JSON Schema ↔ Pydantic Loop

**Status:** Accepted

**Date:** 2026-06-11

**Authors:** Ben Lin

## Context

weirding models three representations of a structured-output shape:

- **A — XML schema document**: the authoring format (plain-attribute annotation
  convention per ADR-0001, or XSD per ADR-0006).
- **B — JSON Schema IR**: the public `dict` returned by `compile()`, the canonical
  intermediate representation (ADR-0002). The native compiler emits a fully **inlined**
  IR — nested objects become inline `{"type":"object","properties":{...}}`, never
  `$ref`/`$defs`. References appear only when an IR originates outside weirding.
- **C — Pydantic v2 model class**: built from the IR by `from_schema()` (ADR-0004).

Today the schema-level pipeline is strictly **one-directional**: `A → B → C`.

| Edge | Function | Present? |
|------|----------|----------|
| A → B | `compile(xml)` | yes |
| B → C | `from_schema(ir)` | yes |
| A → C | `define_model(xml)` | yes (composition) |
| B → B′ | `to_json_schema(ir)` | yes — forward IR→provider transform (ADR-0010), **not** a reverse edge |
| **C → B** | — | **no** |
| **B → A** | — | **no** |
| **C → A** | — | **no** (only `prompt.to_template`, which is a lossy prompt artifact, not a faithful schema) |

The project README and GitHub positioning describe "3-way XML ↔ JSON Schema ↔ Pydantic v2
fungibility." Taken literally — free interconversion among all three — this is **not
currently true**: nothing flows back out of the funnel as a schema. The three missing or
lossy edges are `C → B`, `B → A`, and `C → A`.

This is a decision because the reverse edges are non-obvious in two ways:

1. **`C → B` could be reimplemented or delegated.** Pydantic already exposes
   `model.model_json_schema()` producing draft 2020-12 JSON Schema. The open question is
   whether to reimplement IR extraction from `model_fields`, or to normalize Pydantic's
   native output. The native output omits weirding's `x-weirding-item-tag` extension key
   for hand-written models and may emit `prefixItems` (banned by ADR-0004 / MEMORY rule
   11) for tuple fields.

2. **`B → A` cannot be a total function.** The annotation convention (ADR-0001) has no
   syntax for non-null unions (`anyOf`/`oneOf`/`allOf` beyond the `nullable` pattern) and
   no reference mechanism — so cyclic/self-referential IR cannot be serialized into a
   finite XML tree. A reverse serializer must define, and fail loudly on, the inexpressible
   subset rather than emit silently-wrong XML.

**Alternatives considered:**

- **Do nothing; correct the marketing instead.** Reword the README to claim only a
  forward pipeline plus a two-way *instance* round-trip (`parse`/`to_xml`). Rejected: the
  reverse edges are genuinely useful (import a legacy Pydantic model into the XML-authoring
  workflow; regenerate canonical XML from a hand-edited IR; produce a diffable XML schema
  from a model for review) and the loop is nearly closed already by inlined-IR symmetry.

- **Reimplement `C → B` from `model_fields` directly.** Rejected: duplicates the
  type→schema logic Pydantic already owns and would drift from it across Pydantic
  releases. Normalizing `model_json_schema()` output is strictly less code and tracks
  upstream.

- **Make `B → A` total by inventing union/reference XML syntax.** Rejected: extends the
  ADR-0001 authoring vocabulary for an edge case, breaking the "idiomatic, LLM-promptable
  XML" property that motivated the convention. Failing loudly on the inexpressible subset
  preserves the convention.

- **Route `C → A` through a new dedicated function.** Rejected as redundant: it is exactly
  `dump_xml(to_schema(model))`. A third primitive adds surface area for zero new behavior.

- **Naming `decompile`/`to_xml_schema` for `B → A`.** Considered. `decompile` pairs neatly
  with `compile` but reads as "reverse-engineering." `to_xml_schema` is explicit but visually
  collides with the existing `to_xml`. Chose `dump_xml` (see Decision) to follow the
  Pydantic/`json.dump` "serialize-out" convention.

## Decision

We will add two pure, reverse-edge functions to the public API, and document `C → A` as
their composition rather than a third function.

**`to_schema(model: type[BaseModel]) -> JsonSchemaIR` (edge C → B), inverse of
`from_schema`.** It normalizes `model.model_json_schema()` into IR rather than
reimplementing extraction:

- Array properties lacking `x-weirding-item-tag` receive a synthesized tag via the **same**
  singularization fallback used by `_serializers._item_tag_for_field` (`tags`→`tag`, else
  `item`). This shared heuristic is factored into one helper imported by both call sites so
  they cannot drift.
- `prefixItems` (tuple fields) raises `SchemaError` naming the field — it is unrepresentable
  in the IR (ADR-0004, MEMORY rule 11).
- `$defs`/`$ref` are left intact; resolving them is `dump_xml`'s concern, not this one.

**`dump_xml(ir: JsonSchemaIR) -> str` (edge B → A), inverse of `compile`.** It emits a
canonical ADR-0001 annotation XML document — the structural inverse of
`_schema._element_to_schema`. It inlines any `$ref`/`$defs` first (reusing the resolution
logic from `_export`), then maps each IR construct to its attribute form: `minLength`/
`minItems`→`min`, `maxLength`/`maxItems`→`max`, `enum`→pipe-joined `enum`, the
`anyOf:[T,null]` pattern→`nullable="true"`, a property absent from an object's `required`
list→`required="false"`, and array `items` + `x-weirding-item-tag`→a single child template
element. It raises `SchemaError`, naming the construct, on:

- a non-null `anyOf`/`oneOf`/`allOf` (no union syntax in the convention),
- a cyclic or unresolvable `$ref` (no finite XML serialization).

**`dump_xml` is named, not `to_xml_schema` or `decompile`.** It deliberately sits beside the
existing `to_xml(instance)`: `dump_xml` serializes a **schema IR** to an XML **schema
document**; `to_xml` serializes a model **instance** to XML **data**. Their docstrings must
state this distinction explicitly as the primary disambiguator.

**`C → A` is `dump_xml(to_schema(model))`** — documented as a one-liner, not given its own
function.

Both functions are **pure**: deep-copy their input, never mutate it, perform no I/O, no
logging, no network access — matching `to_json_schema` (ADR-0010) and the project logging
policy.

This decision is **additive and semver-minor**. It does not alter `compile`, `from_schema`,
the IR format (ADR-0002 stability contract is untouched), or any existing behavior.

## Consequences

### Positive

- All six edges of the A ↔ B ↔ C triangle exist; the "3-way fungibility" claim becomes
  literally true (with two documented limits) rather than aspirational.
- New workflows: import a hand-written or legacy Pydantic model into the XML-authoring
  flow (`to_schema`); regenerate canonical, diffable XML from an edited IR or a model
  (`dump_xml`); review a model as XML in a PR.
- `to_schema` tracks Pydantic's own type→schema logic across releases instead of
  duplicating it.
- The round-trip invariants `compile(dump_xml(ir)) == ir` (acyclic, union-free IR) and
  `to_schema(from_schema(ir)) ≈ ir` become testable property-based guarantees, hardening
  the IR contract in both directions.

### Negative

- `dump_xml` is a **partial** function. Cyclic/self-referential IR and non-null unions
  raise rather than serialize. Callers must handle `SchemaError`, and the limitation is a
  permanent property of the ADR-0001 convention, not a backlog item.
- `to_schema` inherits whatever quirks `model_json_schema()` emits (e.g. Pydantic-added
  `title` keys). The IR tolerates these, but `to_schema(from_schema(ir))` is equal only
  *modulo* such additive noise — exact dict equality is not guaranteed.
- Two more names (`dump_xml`, `to_schema`) on the public surface raise the chance of
  confusion with the adjacent `to_xml` and `to_json_schema`. Mitigated by docstrings but
  not eliminated.
- More surface area is more API to keep stable under semver going forward.

### Neutral

- Implementation lives in new modules (`_decompile.py`, `_introspect.py`) so the Tier-2
  protected `_schema.py` and `_models.py` are not touched. The only protected-file edit is
  additive re-exports in the Tier-1 `__init__.py`, which requires explicit approval.
- The singularization fallback is factored out of `_serializers.py` into a shared helper;
  behavior is unchanged, but the helper's location moves.
- Future changes to either function's failure-mode set (e.g. teaching `dump_xml` a new
  expressible construct) are behavioral and should be recorded as a follow-up ADR or noted
  against this one.

## Amendment (2026-06-11, implementation)

Recorded during implementation of this ADR. These are refinements discovered while
building `to_schema` and `dump_xml`; they do not change the decision, only sharpen its
edges.

- **`to_schema` restores `required: []`.** Pydantic's `model_json_schema()` omits the
  `required` key entirely on an object that has no required fields, whereas canonical
  `compile()` IR always carries a `required` list (possibly empty) on every object node.
  `to_schema` therefore restores `required: []` on any object node where Pydantic dropped
  it, keeping `to_schema(from_schema(ir))` structurally symmetric with the canonical IR.

- **Round-trip equivalence is defined modulo `$ref`-inlining (not title noise alone).**
  `from_schema` builds every nested object into a real nested Pydantic `BaseModel`, and
  Pydantic v2 `model_json_schema()` *unconditionally* hoists nested models into top-level
  `$defs` + `$ref`. So `to_schema(from_schema(ir))` for any IR with a nested object is
  `$ref`-bearing, while canonical `compile()` IR is fully inlined. The equivalence
  `to_schema(from_schema(ir)) ≈ ir` is therefore asserted only **after inlining `$defs`/`$ref`
  on the `to_schema` side and stripping additive `title`/`default` keys**. `to_schema` itself
  does NOT inline — that remains `dump_xml`'s job (the Decision above). Only the *test
  comparison* inlines. The fully-canonical round trip `compile(dump_xml(ir)) == ir` is, by
  contrast, asserted as exact dict equality.

- **`dump_xml` accepts both nullable shapes.** The nullable pattern is recognized in both
  `anyOf:[T, {type:null}]` (what `_schema._wrap_nullable` emits) and `type:[T, "null"]`
  (what `to_json_schema(strict=True)` and some foreign IR emit); both map to
  `nullable="true"` plus the inner type's attributes.

- **Out-of-vocabulary keyword handling.** `format` and `additionalProperties` are **dropped**
  (no annotation-convention equivalent; lossy but non-fatal, mirroring the strict-export drops
  of ADR-0010). `const` is **rejected** with `SchemaError` — dropping it would silently lose a
  value constraint rather than a presentational hint.

- **Neutral `$ref` resolution core.** The local-`$ref` resolution logic was factored out of
  `_export` into `_refs.py` with caller-agnostic error wording, so `dump_xml` failures do not
  emit `_export`'s strict-mode-specific phrasing. `_export` wraps the neutral core to keep its
  own message text. This guarantees forward (`_export`) and reverse (`_decompile`) inlining
  cannot drift.
