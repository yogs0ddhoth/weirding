# Architecture Decision Records

ADRs explain *why* this project is designed the way it is.

## How to Read ADRs

Read ADRs before touching a component — not to discover current state, but to understand
why the constraints exist.

## How to Write an ADR

Use the `/adr` command. Copy `template.md` to `NNNN-short-title.md` and fill it in.
ADRs are append-only.

## Index

| # | Title | Status | Date | Summary |
|---|-------|--------|------|---------|
| 0001 | [Schema Annotation Convention](0001-schema-annotation-convention.md) | Accepted | 2026-05-06 | Plain unnamespaced attributes on XML elements; `data-*` and namespace-prefixed rejected; XSD rejected as primary format |
| 0002 | [JSON Schema IR as Public API](0002-json-schema-ir-as-public-api.md) | Accepted | 2026-05-06 | `compile()` returns a public JSON Schema dict; `from_schema()` also public for non-XML callers |
| 0003 | [Validatable Protocol for parse()](0003-validatable-protocol.md) | Accepted | 2026-05-06 | `parse()` accepts any `Validatable` Protocol, not just Pydantic `BaseModel`, enabling non-Pydantic backends |
| 0004 | [json-schema-to-pydantic Engine](0004-json-schema-to-pydantic-engine.md) | Accepted | 2026-05-06 | Runtime model builder; two weirding patches: `additionalProperties`→`extra="forbid"`, `prefixItems` banned from IR |
| 0005 | [x-weirding-item-tag Extension Key](0005-x-weirding-item-tag.md) | Accepted | 2026-05-06 | Array fields carry child tag name in IR as `x-*` extension key for round-trip serialization fidelity |
