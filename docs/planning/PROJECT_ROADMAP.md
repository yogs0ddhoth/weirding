# Project Roadmap

Current development status. Update after each phase is started or completed.

| Status | Phase | Description | Notes |
|--------|-------|-------------|-------|
| ✅ | 00 | Foundation — project setup, CI, core types | |
| ✅ | 01 | Core Pipeline — plain-attribute annotation compiler (ADR-0001), JSON Schema IR, `DTOBuilder` Protocol, `PydanticBuilder`, `compile()` + `from_schema()` + `define_model()` + `parse()` + `to_xml()` | 66 tests |
| ✅ | 02 | Prompt Utilities — `prompt.to_template()`, `prompt.format_error()`, `RetryContext` | 105 tests |
| ✅ | 03 | XSD Support — `weirding[xsd]` extra, `xmlschema`-based IR bridge, dialect auto-detection | 132 tests |
| ✅ | 04 | Distribution — pyproject.toml finalization, CI/CD pipeline, PyPI release, public documentation | ADR-0009 |

**Status key:** Complete · In Progress · Planned

## Current Focus

Ready for v0.1.0 tag and PyPI release (see manual setup steps in `feat/phase-04-distribution` PR)

## Recently Completed

Phase 04 — Distribution (2026-06-02)
