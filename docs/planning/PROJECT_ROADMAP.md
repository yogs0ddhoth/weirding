# Project Roadmap

Current development status. Update after each phase is started or completed.

| Status | Phase | Description | Notes |
|--------|-------|-------------|-------|
| ✅ | 00 | Foundation — project setup, CI, core types | |
| ✅ | 01 | Core Pipeline — plain-attribute annotation compiler (ADR-0001), JSON Schema IR, `DTOBuilder` Protocol, `PydanticBuilder`, `compile()` + `from_schema()` + `define_model()` + `parse()` + `to_xml()` | 66 tests |
| ✅ | 02 | Prompt Utilities — `prompt.to_template()`, `prompt.format_error()`, `RetryContext` | 105 tests |
| ✅ | 03 | XSD Support — `weirding[xsd]` extra, `xmlschema`-based IR bridge, dialect auto-detection | 132 tests |
| ✅ | 04 | Distribution — pyproject.toml finalization, CI/CD pipeline, PyPI release, public documentation | ADR-0009 |
| ✅ | 05 | Ecosystem Interop — `to_json_schema()` provider-ready schema export, model `description`→`__doc__` propagation, integration docs (LangChain/LangGraph, OpenAI/Azure, vLLM/Ollama, Databricks/PySpark), ecosystem-neutral repositioning | ADR-0010, ADR-0011 |
| 🚧 | 06 | Reverse Edges — `to_schema()` (C→B, inverse of `from_schema`) + `dump_xml()` (B→A, inverse of `compile`) close the XML ↔ JSON Schema ↔ Pydantic fungibility loop; C→A is the composition `dump_xml(to_schema(model))` | ADR-0012 |

**Status key:** ✅ Complete · 🚧 In Progress · 📋 Planned

## Current Focus

Phase 06 — Reverse Edges: `to_schema` and `dump_xml` add the two missing reverse edges of the XML ↔ JSON Schema ↔ Pydantic triangle, making the "3-way fungibility" claim literally true (with two documented limits — partiality of `dump_xml` on unions/cycles, and equivalence modulo `$ref`-inlining). Implemented per ADR-0012 on `feat/phase-06-reverse-edges`.

## Recently Completed

Phase 05 — Ecosystem Interop (2026-06-05)
