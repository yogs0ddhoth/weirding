# Plan: ADR-0012 Reverse-Edge Functions (close the fungibility loop)

**Branch:** `feat/phase-06-reverse-edges` (cut from updated `main`)
**ADR:** 0012 (Accepted) — no new ADR required; this plan implements it.
**Semver:** minor (`feat`) — purely additive public API; IR format unchanged (ADR-0002 contract intact).

## Goal

Add the two missing reverse edges of the XML ↔ JSON Schema ↔ Pydantic triangle:
- `to_schema(model: type[BaseModel]) -> JsonSchemaIR` — edge C→B, inverse of `from_schema`.
- `dump_xml(ir: JsonSchemaIR) -> str` — edge B→A, inverse of `compile`.
- C→A is the documented composition `dump_xml(to_schema(model))` — **no third function**.

Both pure (deep-copy in, no mutation/IO/logging), matching `to_json_schema` (ADR-0010).

## Protected-file impact

| File | Tier | Touched? | When |
|------|------|----------|------|
| `src/weirding/__init__.py` | **Tier 1** | **Yes — additive re-exports + `__all__`** | Phase 3 — **requires explicit approval** |
| `src/weirding/_schema.py` | Tier 2 | No | — (design deliberately avoids it) |
| `src/weirding/_models.py` | Tier 2 | No | — (design deliberately avoids it) |
| `src/weirding/_serializers.py` | none | Yes — import shared helper | Phase 1 |

## Simplicity challenge

Simplest approach: one PR with both functions, the helper, exports, and tests. Rejected in
favor of **3 phases** because (1) the Tier-1 `__init__.py` edit must be isolated and
explicitly gated rather than buried in a feature diff; (2) `to_schema` and `dump_xml` are
independent and independently reviewable (Phases 1 and 2 can run in parallel); (3) Phase 1
contains a pure no-behavior-change refactor of `_serializers.py` that should land green
before features build on it. Three phases is the floor that keeps the protected-file edit
isolated; fewer would merge it into feature work.

---

## Phase 1 — Shared item-tag helper + `to_schema` (C→B)

Bundled because the extracted helper exists to serve `to_schema`'s array fallback; a
standalone helper phase would be trivially small.

**Work:**
1. Create `src/weirding/_itemtag.py` with the singularization fallback currently inline in
   `_serializers._item_tag_for_field` (`tags`→`tag`, else `"item"`). Pure string function:
   `item_tag_fallback(field_name: str) -> str`.
2. Modify `_serializers._item_tag_for_field` to call the shared helper for its fallback
   branch. **No behavior change** — existing `test_serializers.py` must stay green.
3. Create `src/weirding/_introspect.py` with `to_schema(model) -> JsonSchemaIR`:
   - Start from `model.model_json_schema()` (deep-copied; never mutate the model).
   - Walk every `type:"array"` property; if it lacks `x-weirding-item-tag`, synthesize one
     via `item_tag_fallback(<property name>)`.
   - Raise `SchemaError` (existing exception) naming the field if `prefixItems` is present
     (ADR-0004 / MEMORY rule 11).
   - Leave `$defs`/`$ref` intact (resolution is `dump_xml`'s job, per ADR-0012).
   - Module docstring cites ADR-0012.

> **Planner correction (the `$ref` trap):** `from_schema` builds every nested object into a
> real nested Pydantic `BaseModel`, and Pydantic v2 `model_json_schema()` *unconditionally*
> hoists nested models into top-level `$defs` + `$ref`. So `to_schema(from_schema(ir))` for
> any IR with a nested object returns a **`$ref`-bearing** dict, while canonical `compile()`
> IR is fully **inlined**. The round-trip equivalence below MUST therefore be asserted
> *after inlining `$defs`/`$ref` on the `to_schema` side* (reuse the neutral ref-resolution
> helper from Phase 2), and modulo **both** Pydantic-added `title` keys **and** `default`
> keys injected for optional fields. `to_schema` itself does NOT inline (that stays
> `dump_xml`'s job per ADR-0012) — only the *test comparison* inlines.

**Files created:** `src/weirding/_itemtag.py`, `src/weirding/_introspect.py`,
`tests/test_introspect.py`, `tests/test_introspect_pbt.py`
**Files modified:** `src/weirding/_serializers.py`
**Protected files:** none
**Tests:**
- Unit: scalar/object/array/nested models; weirding-built model preserves `x-weirding-item-tag`; hand-written model gets the fallback tag; tuple field → `SchemaError`.
- Unit (min/max collapse guard): assert an array model with `minItems`/`maxItems` and a
  string model with `minLength`/`maxLength` both round-trip the *type-correct* keyword
  through `to_schema` — guards against the `json-schema-to-pydantic` collapse silently
  regressing on a dep bump (single-maintainer 0.x dep, MEMORY pinning rule).
- PBT (`test_introspect_pbt.py`, `@settings(max_examples=100)`):
  `to_schema(from_schema(ir))` equals `ir` **after inlining `$defs`/`$ref` on the
  `to_schema` side** and modulo additive `title` + `default` noise. Exact dict equality is
  explicitly NOT asserted (per ADR-0012). Must include nested-object inputs — the naive
  "modulo title only" comparison fails on them.
**Completion signal:** `uv run pytest tests/test_introspect.py tests/test_introspect_pbt.py tests/test_serializers.py` green; `uv run ruff check .` + `uv run pyright` clean.
**Estimate:** ~3h

---

## Phase 2 — `dump_xml` (B→A)

Independent of Phase 1 (`dump_xml` reads `x-weirding-item-tag` straight from the IR; it does
not use the fallback helper). Can run in parallel with Phase 1.

**Work:**
0. **Extract a neutral ref-resolution helper first.** `_export._resolve_ref`/`_lookup_def`
   raise with strict-mode-specific text ("Cannot export schema in strict mode…"). Move the
   resolution *core* into a neutrally-worded shared internal (e.g. `_refs.py`, or a private
   helper both `_export` and `_decompile` import) so `dump_xml` failures don't emit
   misleading "strict mode" messages. `_export` keeps its strict-mode wording by wrapping
   the neutral core. Additive, non-protected.
1. Create `src/weirding/_decompile.py` with `dump_xml(ir) -> str`:
   - Deep-copy input. **Resolve a root-level `$ref` before** deriving the root element name.
     Inline any local `$ref`/`$defs` via the neutral helper. Detect cycles during inlining
     → `SchemaError` naming the ref.
   - Recursive emitter, the structural inverse of `_schema._element_to_schema`:
     - object → element with one child per property; property absent from `required` →
       `required="false"` (else omit; default is required).
     - scalar leaf → `<field type="...">`-style self-closing element with attributes.
     - `minLength`|`minItems` → `min`; `maxLength`|`maxItems` → `max`; `enum` → pipe-joined
       `enum`; `description`/`pattern`/`minimum`/`maximum`/`default` → same-named attribute.
     - **Nullable — two input shapes:** `anyOf:[T,{type:null}]` (what `_schema._wrap_nullable`
       emits) AND `type:["T","null"]` (what `to_json_schema(strict=True)` and some foreign IR
       emit). Both → `nullable="true"` + inner type's attributes. Missing the second shape
       was a planner-flagged gap.
     - `type:"array"` + `items` + `x-weirding-item-tag:"tag"` → `<field type="array"><tag .../></field>`.
   - **Out-of-vocabulary keywords (ADR-0001 has no attribute for these) — explicit
     drop-vs-reject decision, each with a test:** `format` → **drop** (no annotation
     equivalent; lossy but non-fatal, mirrors `to_json_schema` strict drops);
     `additionalProperties` → **drop** (`compile()` never emits it; `extra="forbid"` is not
     expressible in the convention); `const` → **reject** with `SchemaError` (no single-value
     constraint in the convention; surfaces rather than silently loses meaning).
   - Raise `SchemaError` naming the construct on: non-null `anyOf`/`oneOf`/`allOf`;
     cyclic or non-local/unresolvable `$ref`; `const`.
   - Root element name from `ir["title"]` (fallback `"Model"`).
   - `etree.tostring(..., pretty_print=True)`. Module docstring cites ADR-0012.

**Files created:** `src/weirding/_decompile.py`, `tests/test_decompile.py`, `tests/test_decompile_pbt.py`; possibly `src/weirding/_refs.py` (neutral ref helper)
**Files modified:** `src/weirding/_export.py` (wrap neutral ref core — additive, non-protected)
**Protected files:** none
**Tests:**
- Unit: flat scalars; required/optional; constraints (`min`/`max`/`pattern`/`enum`);
  `nullable` in **both** shapes (`anyOf:[T,null]` and `type:[T,"null"]`); arrays with
  explicit + fallback item-tag; nested objects; local `$ref` inlining; **root-level `$ref`**.
- Drop/reject coverage: `format` dropped (not in output); `additionalProperties` dropped;
  `const` → `SchemaError`.
- Failure modes: `oneOf` → `SchemaError`; non-null `anyOf` → `SchemaError`; cyclic `$ref`
  → `SchemaError`; non-local `$ref` → `SchemaError`; unresolvable `$ref` → `SchemaError`.
  Assert the messages are `dump_xml`-appropriate (NOT "strict mode" text).
- PBT (`test_decompile_pbt.py`, recursive strategy `@settings(max_examples=30)`):
  `compile(dump_xml(ir)) == ir` for generated acyclic, union-free IR.
**Completion signal:** `uv run pytest tests/test_decompile.py tests/test_decompile_pbt.py` green; ruff + pyright clean.
**Estimate:** ~5h (raised from 4h: neutral ref helper + expanded drop/reject set + both nullable shapes)

---

## Phase 3 — Public API wiring + docs (Tier-1 gate)

Depends on Phases 1 and 2.

**Work:**
1. **`src/weirding/__init__.py` (Tier 1 — APPROVAL REQUIRED):** import `to_schema` and
   `dump_xml`; add both to `__all__`. Add public docstrings; the `dump_xml` docstring must
   state the distinction from `to_xml` explicitly (`dump_xml` = schema IR → XML *schema
   document*; `to_xml` = model instance → XML *data*). Document C→A as the composition.
2. Re-point a representative subset of Phase 1/2 tests to the public `weirding.to_schema` /
   `weirding.dump_xml` entry points (keep internal-import unit tests too).
3. **Full-hexagon PBT** (`tests/test_fungibility_pbt.py`): author XML → `compile` →
   `from_schema` → `to_schema` → `dump_xml` → `compile`. **Assert canonical equality only at
   the two `compile` outputs** (both fully inlined). The `to_schema` midpoint is `$ref`-bearing
   and is compared *modulo ref-inlining + `title`/`default` noise*, NOT asserted equal to the
   inlined IR — same correction as Phase 1. Generated schemas must include nested objects.
4. Docs:
   - `.claude/memory/MEMORY.md`: add `to_schema`/`dump_xml` to the Public API surface list +
     a Confirmed Standard entry citing ADR-0012; bump current phase note.
   - `README.md`: fungibility claim in prose cites ADR-0012; `CLAUDE.md` project paragraph
     mentions the reverse edges.
   - `docs/planning/PROJECT_ROADMAP.md`: add the phase row.
   - `CHANGELOG.md`: `feat` entry.
   - `mkdocs.yml` / API reference page if functions need autodoc inclusion.

**Files created:** `tests/test_fungibility_pbt.py`
**Files modified:** `src/weirding/__init__.py` **(Tier 1)**, `.claude/memory/MEMORY.md`, `README.md`, `CLAUDE.md`, `docs/planning/PROJECT_ROADMAP.md`, `CHANGELOG.md`, docs/API page
**Protected files:** `src/weirding/__init__.py` (**Tier 1 — explicit approval before edit**)
**Tests:** full suite `uv run pytest` green at ≥90% coverage; ruff + pyright clean.
**Completion signal:** `uv run pytest` (full) green, coverage ≥90%; `uv run ruff check .` + `uv run ruff format .` + `uv run pyright` all clean.
**Estimate:** ~2h

---

## ADR candidates / watch items

- No new ADR needed; ADR-0012 covers the decision. **Append an amendment note to ADR-0012**
  recording the two planner-driven refinements: (1) round-trip equivalence is defined
  *modulo `$ref`-inlining* (because Pydantic hoists nested models into `$defs`/`$ref`), not
  modulo title noise alone; (2) `dump_xml`'s out-of-vocabulary handling — `format`/
  `additionalProperties` dropped, `const` rejected, both nullable shapes accepted.
- A superseding ADR **would** be required only if the team later chose to make `to_schema`
  inline `$ref` itself — that contradicts ADR-0012's decision to leave inlining to `dump_xml`.
- **Watch:** the `json-schema-to-pydantic` min/max keyword collapse is recovered correctly by
  Pydantic today; the Phase 1 collapse-guard unit test exists to catch a silent regression on
  a dep bump (single-maintainer 0.x).

## Pre-flight

`git checkout main && git pull && git checkout -b feat/phase-06-reverse-edges`. (Note: the
uncommitted `.claude/plans/main.md` + `.claude/worktrees/` from session start are unrelated;
do not sweep them into this branch.)
