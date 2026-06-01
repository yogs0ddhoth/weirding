# Project Memory

Project-level memory. Loaded for every agent session. Update this file directly (do not
rely on any external memory system) when you learn something worth persisting across
sessions: a design decision, a confirmed standard, a non-obvious constraint, anything a
future agent would need to avoid re-litigating.

## Core Facts

- **Language / Stack:** Python 3.11+, pydantic>=2.0, lxml>=4.9.2, json-schema-to-pydantic>=0.4, uv
- **Current phase:** Phase 03 — XSD Support (complete); next: Phase 04 — Distribution
- **Framework version:** 0.3.0
- **Roadmap:** `docs/planning/PROJECT_ROADMAP.md`
- **ADRs:** `docs/adr/` — read before touching any component

## Non-Negotiable Rules

1. Zero warnings, zero lint violations on every build
2. No raw PII (user inputs, emails, IDs) in any log statement
3. Never weaken a test threshold to make it pass — fix the code
4. Integration tests must use signal-based completion, not fixed sleeps
5. Always construct `lxml.etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)` — never parse XML without an explicit parser instance
6. No Rust extension — FFI overhead exceeds gains for 1–50KB AI output payloads; wheel matrix is permanent liability; Databricks binary compatibility risk. Revisit only if benchmarks show >10ms pipeline time at required throughput
7. `datamodel-code-generator` is banned as a runtime dep — 50–200ms ruff subprocess + 800ms–2s black cold start. Never import it outside the optional `[codegen]` extra.
8. XSD support is gated on `weirding[xsd]` extra — Phase 01 raises `UnsupportedDialectError("XSD support requires weirding[xsd]")`. No silent failures
9. Forgiving parse mode is OUT — fail fast + retry is correct for the LLM use case. Forgiving parsing swallows the validation signal the retry loop needs
10. JSON Schema dict is the canonical IR and IS publicly exposed via `weirding.compile(xml) -> dict`. All dialect parsers produce it; all model generators consume it. Its structure follows JSON Schema draft 2020-12.
11. `prefixItems` is banned from the JSON Schema IR weirding emits. The library `json-schema-to-pydantic` does not support it. Positional sequences must be represented as named-field objects instead.
12. After `json-schema-to-pydantic` builds a model from a schema with `"additionalProperties": false`, weirding must set `model_config = ConfigDict(extra="forbid")` on that model — the library recognizes the keyword but does not enforce it.
13. Zero pyright errors — `uv run pyright` must exit 0 before every commit. Config: `[tool.pyright]` in `pyproject.toml`, `typeCheckingMode = "standard"`, `reportMissingTypeStubs = "none"`. Note: pyright downloads its Node binary on first run — may fail in network-isolated CI; Phase 04 CI/CD configuration must address this.

## Agent Dispatch Mandate

The top-level session is orchestration only. Dispatch all build, test, and debug work to
agents. Never run verbose or iterative commands in the main session.

## Directory Layout Notes

- Public API: `src/weirding/__init__.py` — `compile()`, `from_schema()`, `define_model()`, `parse()`, `to_xml()`, `DTOBuilder` Protocol, `PydanticBuilder`, `Validatable` Protocol
- Secure XML parsing: `src/weirding/_parser.py` — XMLParser construction lives here exclusively
- Schema compilation: `src/weirding/_schema.py` — plain-attribute annotation → JSON Schema IR
- Model generation: `src/weirding/_models.py` — JSON Schema IR → Pydantic BaseModel (via `build_model()`; used by `PydanticBuilder`)
- Serialization: `src/weirding/_serializers.py` — `to_xml()` + `_xml_to_dict()` (Phase 01)
- Prompt utilities: `src/weirding/prompt.py` — `to_template()`, `format_error()`, `RetryContext`
- XSD bridge (Phase 03, gated): `src/weirding/xsd/`

## Confirmed Standards

- **Schema annotation convention: plain unnamespaced attributes** (ADR-0001 — Accepted 2026-05-06). Canonical attribute vocabulary: `type`, `required` (default `"true"`), `description`, `enum` (pipe-separated), `pattern`, `minimum`, `maximum`, `min` (→`minLength`/`minItems`), `max` (→`maxLength`/`maxItems`), `default`, `nullable` (→ `anyOf: [{type: T}, {type: null}]`, draft 2020-12 form). Array fields use `type="array"` with a single child element as item template; the child tag is stored as `x-weirding-item-tag` in the IR (ADR-0005 pending). `data-*` and namespace-prefixed conventions explicitly rejected. XSD rejected as primary authoring format — too verbose for LLM prompt templates, no maintained Python runtime converter exists.
- **Dialect auto-detection in `define_model()`**: root element `{http://www.w3.org/2001/XMLSchema}schema` → XSD path; presence of weirding annotation attributes in the tree → native-annotation path; neither → `UnsupportedDialectError`
- **`JsonSchemaIR` type alias** (added 2026-05-31): `src/weirding/_types.py` declares `JsonSchemaIR: TypeAlias = dict[str, Any]`. Applied across all 5 IR-handling modules. Exported from `weirding.__all__` — callers may annotate `schema: weirding.JsonSchemaIR`. Alias is pyright-transparent (no cast sites required). `_types.py` deliberately omits `from __future__ import annotations` — the one exception to the project-wide pattern; deferring annotations in a types-only module is a footgun. `_XSD_TYPE_MAP` in `_bridge.py` typed `dict[str, JsonSchemaIR]`. `_type_to_ir` renamed → `_primitive_to_ir` (pure map-lookup, not general converter).
- **Public API surface** (all in `weirding.__init__`):
  - `compile(xml: str | bytes) -> JsonSchemaIR` — XML schema → JSON Schema IR dict (the core product; publicly exposed)
  - `from_schema(schema: JsonSchemaIR, *, name: str = "Model", builder: DTOBuilder | None = None) -> type` — JSON Schema IR → typed DTO class; default builder is `PydanticBuilder()` → `type[BaseModel]`; overloaded for static type safety
  - `define_model(xml: str | bytes, *, builder: DTOBuilder | None = None) -> type` — convenience: `from_schema(compile(xml), name=<root_tag>, builder=builder)`
  - `parse(xml: str | bytes, model: Validatable) -> Any` — XML data → validated instance; `model` parameter is a `Validatable` Protocol
  - `to_xml(instance: BaseModel) -> str` — model instance → XML string
  - `DTOBuilder` Protocol — `build(schema, *, name) -> type`; symmetric with `Validatable`; both ends of pipeline are backend-neutral
  - `PydanticBuilder` — default `DTOBuilder` implementation; wraps `json-schema-to-pydantic` with two patches
- **`Validatable` Protocol**: `def model_validate(cls, data: dict[str, Any]) -> Any` classmethod. Satisfied by every Pydantic `BaseModel` subclass. Allows `parse()` to work with future non-Pydantic validators without changing the public signature.
- **Model name derivation**: root XML element tag, sanitized to a valid Python identifier (`re.sub(r'[^A-Za-z0-9_]', '_', tag).lstrip('0123456789') or 'Model'`). Passed as `name` to `from_schema()`.
- **`json-schema-to-pydantic>=0.4` confirmed** as the engine for `build_model()` / `from_schema()`. Two weirding-owned patches required: (1) post-creation `extra="forbid"` when schema has `"additionalProperties": false`; (2) IR compiler never emits `prefixItems` (rule 11).
- Base dependencies: `pydantic>=2.0`, `lxml>=4.9.2`, `json-schema-to-pydantic>=0.4`; XSD optional dep: `xmlschema>=3.0` (in `[xsd]` extra only)
- **XSD bridge (`src/weirding/xsd/_bridge.py`)**: `xmlschema.XMLSchema(root_element, defuse="always")` — pass the already-parsed lxml element, always `defuse="always"` (NOT remote or default). Type map keys are Clark-notation URIs (`{http://www.w3.org/2001/XMLSchema}string`), NOT `xs:`-prefixed names. `_iter_elements()` guards against `xs:simpleContent` via `isinstance(content, XsdGroup)` — without this guard, simpleContent raises TypeError. XSD bridge never emits `"additionalProperties": false`; `extra="forbid"` patch does not fire for XSD-derived models (intentional). ADR-0006 documents library choice and security posture (pending authoring).
- **Future capability targets** (inform all design decisions): enterprise document ingestion (Word/Office Open XML, Excel XLSX), Anthropic structured output and XML capabilities, Kubernetes MCP server/gateway payloads, Databricks AI-aided data science and ETL pipelines. Attribute convention and IR design must remain idiomatic XML across all these contexts.
- Prototype at `C:\Users\becom\Developer\Lithium\packages\xml-pydantic` — port `schema.py` (native-XML annotation compiler) and `serializers.py` (model→XML); replace `ET.fromstring()` with `make_parser()`; replace `datamodel-code-generator` with `json-schema-to-pydantic`. Note: prototype used `data-*`; do NOT carry that convention forward.
- **Docstring style:** Google-style enforced by `ruff D, convention = "google"`. Protocol
  method stubs require one-liner docstrings (D102). Test files fully exempt via
  `per-file-ignores = ["D"]`. Do not enable DOC rules (DOC201/DOC501) — unstable in ruff 0.15.

- **`pytest.mark.parametrize` policy:** Class-based grouping preferred for fixture-driven
  suites (see `test_xsd.py`). `@pytest.mark.parametrize` allowed and encouraged for
  tabular/data-driven cases with >3 inputs. No blanket prohibition.

- **Coverage threshold:** `--cov-fail-under=N` enforced in `pyproject.toml` addopts (set
  Phase 1). Never lower this value to make a failing test pass — fix the missing coverage.

- **IR version stability contract:** `JsonSchemaIR` format changes that remove or rename
  existing keys are breaking changes (semver **major**). Additions of new optional keys
  (including new `x-weirding-*` extension keys) are **minor**. Applies regardless of whether
  the change also modifies a Python function signature. Recorded in ADR-0002 appendix.

- **Async policy:** weirding is synchronous by design (`lxml` is synchronous; no async
  needed for 1–50KB AI payloads). No async support until a concrete streaming use case is
  confirmed and benchmarked. Do not accept PRs adding `async`/`await` to the public pipeline
  without a new plan and ADR.

- **Logging policy:** weirding emits no log statements. Callers own their observability
  stack. Adding logging to library code requires explicit approval — it risks capturing user
  data in caller log sinks (privacy violation per ETHOS.md).

- **Dependency pinning strategy:** Single-maintainer 0.x packages must be pinned
  `>=X.Y.Z,<NEXT_MAJOR` (e.g., `json-schema-to-pydantic>=0.4.7,<1`). Stable
  multi-maintainer packages use `>=X.Y` open upper bounds. Never add a new single-maintainer
  0.x dep without documenting the escape hatch in an ADR.

- **PydanticBuilder placement:** Protocol implementations belong in the module that owns
  the capability (`_models.py`), not in the routing module (`__init__.py`). Current
  `PydanticBuilder` location is documented technical debt; relocation is a separate
  ADR-gated plan. Do not add more Protocol implementations to `__init__.py`.

- **PBT file separation:** Hypothesis property-based tests must live in `*_pbt.py` files
  separate from deterministic tests. Use `pytest -k "not pbt"` for fast-iteration runs.
  Settings: `@settings(max_examples=100)` for leaf strategies, `@settings(max_examples=30)`
  for recursive tree strategies. Commit `.hypothesis/` directory (small; enables CI replay).
