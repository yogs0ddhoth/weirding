# Project Roadmap

Current development status. Update after each phase is started or completed.

| Status | Phase | Description | Notes |
|--------|-------|-------------|-------|
| ✅ | 00 | Foundation — project setup, CI, core types | |
| ✅ | 01 | Core Pipeline — plain-attribute annotation compiler (ADR-0001), JSON Schema IR, `DTOBuilder` Protocol, `PydanticBuilder`, `compile()` + `from_schema()` + `define_model()` + `parse()` + `to_xml()` | 66 tests |
| ✅ | 02 | Prompt Utilities — `prompt.to_template()`, `prompt.format_error()`, `RetryContext` | 105 tests |
| 📋 | 03 | XSD Support — `weirding[xsd]` extra, `xmlschema`-based IR bridge, dialect auto-detection | |
| 📋 | 04 | Distribution — pyproject.toml finalization, CI/CD pipeline, PyPI release, public documentation | |

**Status key:** Complete · In Progress · Planned

## Current Focus

Phase 03 — XSD Support

## Recently Completed

Phase 02 — Prompt Utilities (2026-05-06)
