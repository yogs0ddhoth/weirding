# Project Memory

Project-level memory. Loaded for every agent session. Update this file directly (do not
rely on any external memory system) when you learn something worth persisting across
sessions: a design decision, a confirmed standard, a non-obvious constraint, anything a
future agent would need to avoid re-litigating.

## Core Facts

- **Language / Stack:** Python 3.11+, pydantic>=2.0, lxml>=4.9.2, json-schema-to-pydantic>=0.4, uv
- **Current phase:** Phase 01 — Core Pipeline (complete)
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
- **Public API surface** (all in `weirding.__init__`):
  - `compile(xml: str | bytes) -> dict` — XML schema → JSON Schema IR dict (the core product; publicly exposed)
  - `from_schema(schema: dict, *, name: str = "Model", builder: DTOBuilder | None = None) -> type` — JSON Schema IR → typed DTO class; default builder is `PydanticBuilder()` → `type[BaseModel]`; overloaded for static type safety
  - `define_model(xml: str | bytes, *, builder: DTOBuilder | None = None) -> type` — convenience: `from_schema(compile(xml), name=<root_tag>, builder=builder)`
  - `parse(xml: str | bytes, model: Validatable) -> Any` — XML data → validated instance; `model` parameter is a `Validatable` Protocol
  - `to_xml(instance: BaseModel) -> str` — model instance → XML string
  - `DTOBuilder` Protocol — `build(schema, *, name) -> type`; symmetric with `Validatable`; both ends of pipeline are backend-neutral
  - `PydanticBuilder` — default `DTOBuilder` implementation; wraps `json-schema-to-pydantic` with two patches
- **`Validatable` Protocol**: `def model_validate(cls, data: dict[str, Any]) -> Any` classmethod. Satisfied by every Pydantic `BaseModel` subclass. Allows `parse()` to work with future non-Pydantic validators without changing the public signature.
- **Model name derivation**: root XML element tag, sanitized to a valid Python identifier (`re.sub(r'[^A-Za-z0-9_]', '_', tag).lstrip('0123456789') or 'Model'`). Passed as `name` to `from_schema()`.
- **`json-schema-to-pydantic>=0.4` confirmed** as the engine for `build_model()` / `from_schema()`. Two weirding-owned patches required: (1) post-creation `extra="forbid"` when schema has `"additionalProperties": false`; (2) IR compiler never emits `prefixItems` (rule 11).
- Base dependencies: `pydantic>=2.0`, `lxml>=4.9.2`, `json-schema-to-pydantic>=0.4`
- **Future capability targets** (inform all design decisions): enterprise document ingestion (Word/Office Open XML, Excel XLSX), Anthropic structured output and XML capabilities, Kubernetes MCP server/gateway payloads, Databricks AI-aided data science and ETL pipelines. Attribute convention and IR design must remain idiomatic XML across all these contexts.
- Prototype at `C:\Users\becom\Developer\Lithium\packages\xml-pydantic` — port `schema.py` (native-XML annotation compiler) and `serializers.py` (model→XML); replace `ET.fromstring()` with `make_parser()`; replace `datamodel-code-generator` with `json-schema-to-pydantic`. Note: prototype used `data-*`; do NOT carry that convention forward.
