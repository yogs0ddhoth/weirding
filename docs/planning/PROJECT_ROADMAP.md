# Project Roadmap

Current development status. Update after each phase is started or completed.

| Status | Phase | Description | Notes |
|--------|-------|-------------|-------|
| ✅ | 00 | Foundation — project setup, CI, core types | |
| ✅ | 01 | Core Pipeline — plain-attribute annotation compiler (ADR-0001), JSON Schema IR, `DTOBuilder` Protocol, `PydanticBuilder`, `compile()` + `from_schema()` + `define_model()` + `parse()` + `to_xml()` | 66 tests |
| ✅ | 02 | Prompt Utilities — `prompt.to_template()`, `prompt.format_error()`, `RetryContext` | 105 tests |
| ✅ | 03 | XSD Support — `weirding[xsd]` extra, `xmlschema`-based IR bridge, dialect auto-detection | 132 tests |
| ✅ | 04 | Distribution — pyproject.toml finalization, CI/CD pipeline, PyPI release, public documentation | ADR-0009 |
| 🚧 | 05 | Ecosystem Interop — `to_json_schema()` provider-ready schema export, model `description`→`__doc__` propagation, integration docs (LangChain/LangGraph, OpenAI/Azure, vLLM/Ollama, Databricks/PySpark), ecosystem-neutral repositioning | ADR-0010, ADR-0011 |

**Status key:** ✅ Complete · 🚧 In Progress · 📋 Planned

## Current Focus

Phase 05 — Ecosystem Interop: code seams (`to_json_schema`, `__doc__` propagation) complete; integration docs and repositioning in progress on `feat/phase-05-ecosystem-interop`.

## Recently Completed

Phase 04 — Distribution (2026-06-02)
