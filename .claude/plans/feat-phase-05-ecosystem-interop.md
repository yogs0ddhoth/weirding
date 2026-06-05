# IMPLEMENTATION PLAN: Phase 05 — Ecosystem Interop

**Branch:** `feat/phase-05-ecosystem-interop` (create from `main` before implementing)
**Phase context:** Phases 00–04 complete; 0.1.0 shipped (PR #5 merged, docs live). This is the first post-release feature phase.
**Created:** 2026-06-05
**Relevant ADRs:** ADR-0002 (JSON Schema IR as public API), ADR-0005 (x-weirding-item-tag), ADR-0008 (MkDocs toolchain)
**Scope source:** `/ideate ecosystem-interop` (2026-06-05), four researcher reports (OpenAI/Azure, LangChain/LangGraph, open-weight vLLM/Ollama, Databricks/PySpark)

---

## Context

weirding is positioned as "purpose-built for the Claude structured output workflow," but its core utilities (`to_template`, `format_error`, `RetryContext`) make no API calls and have no provider dependency — they are already neutral. The gap is **reach plus two small seams**, not a rewrite. Research confirmed that every provider seam collapses to **one shared, pure schema-export helper** plus documentation:

- **OpenAI/Azure** strict Structured Outputs reject weirding's IR as-is (need `additionalProperties:false` everywhere, all-`required`, unsupported keywords stripped).
- **Databricks `ai_query` `responseFormat`** is the *strictest* consumer — additionally forbids `anyOf` (require collapsed `{"type":[T,"null"]}`) and `pattern`, max 64 keys. A transform built for the OpenAI∩Databricks **intersection** satisfies both.
- **open-weight (vLLM/Ollama)** accept the IR essentially as-is; a clean variant stripping `x-weirding-*` is the portable artifact. XML template + retry remains the fallback for non-guided runtimes.
- **LangChain/LangGraph** already work via bare `with_structured_output(Model)` — docs-only, except one tiny fix: weirding's dynamically-created models have `__doc__ = None`, which yields **silently empty tool descriptions**.

ADR-0002's negative-consequences section already anticipated the strip step; this phase formalizes it.

## Goal

Reposition weirding as ecosystem-neutral (Claude = one peer) and remove the friction for four first-class targets, via **docs + two thin seams only** — no provider abstraction, no `weirding.llm`, no LLM API call, no new required runtime dependency, no logging.

---

## Simplicity Challenge

**Simplest approach (1 phase):** one PR with the helper, the `__doc__` fix, and all four docs pages. Rejected — it mixes a **Tier-1** protected change (`__init__.py` export), a **Tier-2** protected change (`_models.py`, a silent-model-regression hot path), **two** distinct ADRs, and four doc pages into a single reviewable unit. A docs nit would block the code; a `_models.py` regression would be entangled with an additive helper.

**Two phases (code + docs):** viable, but bundles the Tier-1 additive helper with the riskier Tier-2 `_models.py` change under one approval. Splitting them lets the hot-path change be isolated and independently revertible.

**Three phases (chosen):** each code change is gated by its own ADR and protected-file approval and is independently buildable/testable; docs come last so they reference shipped, tested symbols. Justified by two separate protected-file tiers + two ADRs + a doc surface.

---

## Phase 1 — Shared schema-export helper (`to_json_schema`)

**Goal:** Add one pure, dependency-free function that turns the public IR into a provider-ready JSON Schema: a clean variant for permissive backends and a strict variant accepted unmodified by OpenAI, Azure, and Databricks `ai_query`.

**Files created:**
- `src/weirding/_export.py` — pure `to_json_schema(ir: JsonSchemaIR, *, strict: bool = False) -> dict`
- `tests/test_export.py`
- `docs/adr/0010-schema-export-helper.md`

**Files modified:**
- `src/weirding/__init__.py` — export `to_json_schema`, add to `__all__`  ⚠️ **Tier 1 protected**
- `.claude/memory/MEMORY.md` — record the helper + intersection-subset contract

**Protected files:**
- `src/weirding/__init__.py` (**Tier 1** — ask before any change). *Why required:* the public API surface is where callers reach the helper; the alternative (an undocumented `weirding._export` import) defeats the purpose and contradicts ADR-0002's "no undocumented internal import" principle. Change is **purely additive** (one new name in `__all__`), so semver-**minor** per ADR-0002's IR/format evolution policy.

**Design (for ADR-0010):**
- `strict=False`: deep-copy; strip all `x-weirding-*` extension keys (formalizes ADR-0002's documented strip step); leave everything else intact. This is clean JSON Schema draft 2020-12 for vLLM/Ollama/`jsonschema`.
- `strict=True`: the OpenAI∩Databricks intersection — recursively (a) set `additionalProperties:false` on every object, (b) promote every property to `required`, (c) collapse nullable `anyOf:[{...},{"type":"null"}]` → `{"type":[T,"null"]}` (Databricks forbids `anyOf`; OpenAI accepts the collapsed form), (d) strip unsupported keywords everywhere (`pattern`, `format`, `minimum`, `maximum`, `multipleOf`, `min/maxLength`, `min/maxItems`, `uniqueItems`, `default`, `patternProperties`, `propertyNames`, `min/maxProperties`) and all `x-weirding-*`.
- **Root special-case:** refuse a null-wrapped (`anyOf`) root with a clear `weirding` error rather than emit a schema the providers reject.
- **`$ref`/`$defs` (planner-required):** Databricks `ai_query` forbids `$ref`, but ADR-0002 declares local `#/$defs/...` refs part of the IR contract and OpenAI strict mode accepts them — so the intersection is *narrower* than the keyword-strip list. In `strict=True`, **inline all local `$ref`/`$defs`**; if a ref cannot be resolved locally, raise a clear `weirding` error. The native-annotation compiler currently inlines and emits no `$ref`, but the XSD dialect (and caller-built IR) may, and ADR-0002 requires identical IR shape across dialects — so the helper must handle it, not assume its absence. Test asserts the chosen behavior.
- **64-key limit (planner-required):** Databricks caps `ai_query` schemas at 64 keys. In `strict=True`, **raise a clear `weirding` error when the transformed schema exceeds 64 keys**, consistent with the root-anyOf "refuse rather than emit a rejected schema" stance; document the limit in the docstring. (OpenAI's far higher limits are not enforced — only the binding Databricks cap is.)
- **Input contract:** IR dict in, plain `dict` out (not a model — callers have `compile()`). Pure function: no I/O, no logging, no network, no mutation of input.
- **Lossiness:** strict mode is lossy by design (drops constraints) and changes optional→required+null semantics. Documented in the docstring and the ADR. v1 returns only the dict (no dropped-keyword report) to keep the surface minimal; revisit if requested — never via a log statement (logging policy).

**Completion signal:**
- `tests/test_export.py` asserts: strict output has `additionalProperties:false` on every object and all properties in `required`; nullable collapsed to type-array; no banned keyword present (incl. no `anyOf`/`oneOf`/`allOf`/`pattern`/`prefixItems`/`$ref`); no `x-weirding-*` present; local `$ref`/`$defs` inlined (and unresolvable `$ref` raises); >64-key strict schema raises; non-strict strips only `x-weirding-*` and is otherwise byte-equivalent in structure; null-wrapped root raises; input dict is not mutated. The strict-test keyword allowlist matches the verified vendor sets (OpenAI: reject `default`, root-`anyOf`; Databricks: reject `anyOf`/`oneOf`/`allOf`, `pattern`, `prefixItems`, `$ref`, only `[type,"null"]` nullable, ≤64 keys).
- A property-based test (`tests/test_export_pbt.py`, optional within estimate) feeding `compile()` output of varied schemas through `to_json_schema(strict=True)` and validating the result against the documented OpenAI/Databricks keyword allowlist.
- `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest` all exit 0; coverage ≥ existing threshold.

**ADR candidate:** **YES — ADR-0010.** Public-API addition under the IR contract; trade-off between one intersection helper vs. per-provider helpers; lossy transform semantics. Must also record: (a) the `$ref` decision (inline vs. reject) and the 64-key decision (reject) as the credible-alternatives trade-off; (b) a note that stripping `format`/`minimum`/`maximum` for Databricks is a **conservative** choice (their support status is undocumented, not docs-mandated removal) so a future maintainer does not "fix" it by re-adding them. Author with `/adr` before merge.

**Estimate:** 3–4 hours

---

## Phase 2 — Generated-model description propagation

**Goal:** weirding-generated models carry the IR's top-level `description` into their `__doc__`, so LangChain/Anthropic tool definitions get a real description instead of an empty one.

**Files modified:**
- `src/weirding/_models.py` — set `__doc__` from `schema.get("description")` on the generated class  ⚠️ **Tier 2 protected**
- `tests/test_models.py` (or the relevant existing model test) — assert propagation
- `docs/adr/0011-model-description-propagation.md`

**Protected files:**
- `src/weirding/_models.py` (**Tier 2** — explain why alternatives are insufficient). *Why required & why alternatives fail:* the empty-`__doc__` defect lives exactly in the `type(name, (model,), {...})` construction in this module; `__doc__` is not inherited from the base, so it resolves to `None`. A LangChain adapter cannot fix it without re-wrapping the class (rejected in ideation as scope creep + dependency coupling). Leaving it `None` silently degrades tool-calling accuracy for every LangChain/Anthropic user. The fix is one key in the existing `type(...)` call — minimal, on the hot path but additive metadata only.

**Design (for ADR-0011):**
- When the IR has a top-level `description`, include `"__doc__": <description>` in the generated class namespace. When absent, behavior is unchanged (`__doc__` stays `None`).
- Must not disturb the existing `extra="forbid"` patch (MEMORY.md rule 12) or any field metadata. Verified by re-running the round-trip and `extra="forbid"` tests.

**Completion signal:**
- Test: a model built from an IR with `description` has `Model.__doc__ == <description>` and `Model.model_json_schema()["description"] == <description>`; a model from an IR without `description` has `__doc__ is None`; existing round-trip and `extra="forbid"` tests still pass.
- `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest` all exit 0; coverage maintained.

**ADR candidate:** **YES — ADR-0011** (short). Touches a Tier-2 protected file; cross-component impact (changes what LangChain/Anthropic see). Author with `/adr` before merge.

**Estimate:** 1.5–2 hours

---

## Phase 3 — Integration docs & repositioning

**Goal:** Four runnable integration guides plus a repositioning pass so weirding reads as ecosystem-neutral.

**Files created:**
- `docs/integrations/langchain.md` — bare `with_structured_output(Model)`; LangGraph Pydantic state; the OpenAI strict-mode `method="function_calling"` escape hatch; nested-`$ref` note for Ollama/Llama; checkpointing note (instances serialize; the class is not picklable by name).
- `docs/integrations/openai-azure.md` — `to_json_schema(compile(xml), strict=True)` → `response_format`; Azure API-version/model gating noted as caller concerns.
- `docs/integrations/open-weight.md` — vLLM `response_format`/structured outputs (recommend `backend=auto`); Ollama `format`; `to_json_schema(strict=False)` as the clean artifact; `to_template` + `parse`/`RetryContext` as the unguided fallback.
- `docs/integrations/databricks-pyspark.md` — `ai_query` `responseFormat` via `to_json_schema(strict=True)`; the **build-the-model-inside-the-UDF** executor-serialization recipe (lead with it) + `pydantic>=2.5`; `parse`+`RetryContext` inside `pandas_udf`/`mapInPandas` with a hard max-retries cap; delegate `StructType` to **`sparkdantic`** (no dependency added).

**Files modified:**
- `mkdocs.yml` — add an "Integrations" nav section (4 pages)
- `README.md` — reposition the project description (Claude → one peer of LangChain/OpenAI/Azure/open-weight/Databricks); keep XML-first identity
- `CLAUDE.md` and `pyproject.toml` `description` — align the one-line project blurb with the README repositioning
- `docs/index.md` (or equivalent landing page) — mirror the repositioning
- `CHANGELOG.md` — `### Added` (`to_json_schema`), `### Changed` (model description propagation; positioning) under `[Unreleased]`
- `docs/planning/PROJECT_ROADMAP.md` — add Phase 05, mark complete on finish
- `.claude/memory/MEMORY.md` — note LangChain/Databricks now first-class documented targets

**Protected files:** none (README, CLAUDE.md, docs, pyproject metadata are not in the protected tiers).

**Privacy requirement (non-negotiable, blocks merge):** every example UDF/retry snippet logs only outcomes/counts — **never** raw inputs or full LLM responses (which would write user data to Spark executor logs / the Spark UI keyed by partition). Add an explicit privacy note on the Databricks page; caution that `format_error`/`RetryContext` output can embed offending field values. Honors MEMORY.md rule 2 and `format_error`'s existing `include_input=False`.

**Completion signal:**
- `uv run mkdocs build --strict` exits 0 (ADR-0008 zero-warning docs policy) with all four pages in nav and no broken cross-references.
- A reviewer reading README + docs landing sees no "Claude-only" framing.
- Each integration page's code snippet uses only public symbols that exist after Phases 1–2.

**ADR candidate:** none (docs/positioning only).

**Estimate:** 4–5 hours

---

## Total Estimate: ~9–11 hours

---

## ADR Candidates (summary)

| ADR | Title | Why |
|-----|-------|-----|
| 0010 | Schema-export helper (`to_json_schema`) | Public-API addition under the IR contract; one intersection helper vs. per-provider; lossy strict transform |
| 0011 | Generated-model description propagation | Tier-2 protected-file change; alters what LangChain/Anthropic tool definitions receive |

---

## Protected Files Requiring Approval

| File | Tier | Phase | Nature |
|------|------|-------|--------|
| `src/weirding/__init__.py` | 1 — ask before any change | 1 | Additive export of `to_json_schema` (semver minor) |
| `src/weirding/_models.py` | 2 — explain alternatives | 2 | One key added to the generated-class `type(...)` call; additive metadata |

`_parser.py` and `_schema.py` are **not** touched by this plan.

---

## Out of Scope (explicit)

- ❌ `weirding.llm` / any provider abstraction or API-calling layer (conflicts with logging/async/"callers own their LLM call" policies)
- ❌ IR → Spark `StructType` helper (document `sparkdantic`; adding PySpark re-introduces the binary-compat liability of MEMORY.md rule 6)
- ❌ `weirding[langchain]` adapter extra (bare composition already works)
- ❌ JSON-in-prompt template generator (no evidence it beats XML template + retry for 1–50KB payloads)

---

## Post-Completion Checklist

- [ ] `to_json_schema` exported, tested (strict satisfies OpenAI∩Databricks; non-strict strips `x-weirding-*`; root null-wrap raises; input not mutated)
- [ ] Generated models propagate `description` → `__doc__`; `extra="forbid"` + round-trip tests still green
- [ ] ADR-0010 and ADR-0011 authored and indexed
- [ ] Four integration docs build under `mkdocs build --strict`; privacy note present on Databricks page
- [ ] README / CLAUDE.md / pyproject description / docs landing repositioned (Claude = peer)
- [ ] CHANGELOG updated; `PROJECT_ROADMAP.md` Phase 05 marked complete; `MEMORY.md` updated
- [ ] PR against `main`

---

AWAITING HUMAN APPROVAL BEFORE PROCEEDING.
State: PROCEED, MODIFY [description], or REJECT.
