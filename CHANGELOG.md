# Changelog

All notable changes to weirding are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Changed
- ruff D rules with Google docstring convention now enforced across `src/`
- `json-schema-to-pydantic` version pin tightened to `>=0.4.7,<1`

### Added
- Coverage threshold: 90% minimum enforced in CI (`--cov-fail-under=90`)
- Nine project standards codified: async policy, logging policy, dependency pinning strategy,
  `JsonSchemaIR` semver contract, docstring convention, parametrize policy, PBT file
  separation, `PydanticBuilder` placement, and coverage threshold

## [0.1.0] — 2026-04-30

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
