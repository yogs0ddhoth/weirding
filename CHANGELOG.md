# Changelog

All notable changes to weirding are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Added
- `weirding.to_schema(model)` — reverse edge C→B: derive a JSON Schema IR dict from a
  Pydantic v2 model class (the inverse of `from_schema`), normalizing
  `model.model_json_schema()` so it tracks Pydantic's own type→schema logic
- `weirding.dump_xml(ir)` — reverse edge B→A: serialize a JSON Schema IR back to a canonical
  ADR-0001 XML *schema document* (the inverse of `compile`). Distinct from `to_xml`, which
  serializes a model *instance* to XML *data*. Together with `to_schema` this closes the
  XML ↔ JSON Schema ↔ Pydantic fungibility loop; `C→A` is the composition
  `dump_xml(to_schema(model))` (ADR-0012)
- `weirding.to_json_schema(ir, *, strict=False)` — provider-ready JSON Schema export from
  the IR. `strict=False` strips `x-weirding-*` for a clean draft 2020-12 artifact
  (vLLM/Ollama/jsonschema); `strict=True` emits the OpenAI ∩ Databricks intersection
  accepted by OpenAI/Azure Structured Outputs and Databricks `ai_query` `responseFormat`
- Integration guides for LangChain/LangGraph, OpenAI/Azure, open-weight runtimes
  (vLLM/Ollama), and Databricks/PySpark

### Changed
- Generated models now propagate the schema's top-level `description` to `Model.__doc__`,
  so LangChain/Anthropic tool definitions receive a real description instead of an empty one
- Positioning is now ecosystem-neutral — Claude is one peer among first-class
  structured-output targets (LangChain/LangGraph, OpenAI/Azure, vLLM/Ollama, Databricks)

## [0.1.0] — 2026-05-31

### Added
- `compile(xml)` — XML schema → JSON Schema IR dict (plain-attribute annotation dialect)
- `define_model(xml)` — XML schema → Pydantic v2 BaseModel (convenience wrapper)
- `from_schema(ir, *, name, builder)` — JSON Schema IR → Pydantic model (direct IR path)
- `parse(xml, model)` — XML data → validated Pydantic instance
- `to_xml(instance)` — Pydantic instance → XML string (full round-trip)
- `prompt.to_template(model)` — Pydantic model → XML prompt template for LLM structured output
- `prompt.format_error(error, model)` — ValidationError → human-readable retry message (PII never echoed)
- `prompt.RetryContext` — stateful retry loop helper for LLM → parse → retry workflows
- `DTOBuilder` Protocol — extensible model-building backend abstraction
- `PydanticBuilder` — default DTOBuilder backed by json-schema-to-pydantic
- `Validatable` Protocol — validation backend abstraction for `parse()`
- `JsonSchemaIR` TypeAlias — public type for the JSON Schema IR dict
- `weirding[xsd]` optional extra — full XSD schema support via xmlschema bridge
  - Dialect auto-detected from root element tag (`{http://www.w3.org/2001/XMLSchema}schema`)
- Secure XML parsing: `resolve_entities=False`, `no_network=True`, `load_dtd=False`
- XXE and billion-laughs attack prevention verified by security tests
- Coverage threshold: 90% minimum enforced in CI (`--cov-fail-under=90`)
- Nine project standards codified: async policy, logging policy, dependency pinning strategy,
  `JsonSchemaIR` semver contract, docstring convention, parametrize policy, PBT file
  separation, `PydanticBuilder` placement, and coverage threshold

### Changed
- ruff D rules with Google docstring convention now enforced across `src/`
- `json-schema-to-pydantic` version pin tightened to `>=0.4.7,<1`
