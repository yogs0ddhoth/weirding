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
| 0006 | [XSD Support — Library Choice, Security Posture, and Type Mapping](0006-xsd-support-library-and-security-posture.md) | Accepted | 2026-05-28 | `xmlschema>=3.0` as optional `[xsd]` dep; `defuse="always"` mandatory; Clark-notation URI keys for type map |
| 0007 | [Type Checking Adoption — pyright, standard mode, suppression scope](0007-type-checking-adoption.md) | Accepted | 2026-05-31 | pyright over mypy; `standard` mode; global `reportMissingTypeStubs = "none"`; file-level suppression in `_bridge.py` |
| 0008 | [MkDocs + Material Documentation Toolchain](0008-mkdocs-material-documentation-toolchain.md) | Accepted | 2026-06-01 | MkDocs 1.6 + Material 9.7 + mkdocstrings-python; Sphinx and pdoc rejected; `theme.font: false` for privacy |
| 0009 | [PyPI Publish Authentication — OIDC Trusted Publishing vs. API Token](0009-pypi-oidc-trusted-publishing.md) | Accepted | 2026-06-02 | OIDC trusted publishing via `pypa/gh-action-pypi-publish`; no long-lived API token stored in GitHub Secrets |
| 0010 | [Schema-Export Helper (`to_json_schema`)](0010-schema-export-helper.md) | Accepted | 2026-06-05 | Pure boundary transform of the IR; `strict=True` emits the OpenAI ∩ Databricks intersection (inline `$ref`, collapse nullable, strip unsupported keywords, ≤64 keys); `strict=False` strips `x-weirding-*` |
| 0011 | [Generated-Model Description Propagation](0011-model-description-propagation.md) | Accepted | 2026-06-05 | Top-level schema `description` → generated model `__doc__`, so LangChain/provider tool definitions get a real description; fixes empty tool descriptions without an adapter |
| 0012 | [Reverse-Edge Functions — Closing the Fungibility Loop](0012-reverse-edge-fungibility.md) | Accepted | 2026-06-11 | Add `to_schema(model)` (C→B, inverse of `from_schema`) and `dump_xml(ir)` (B→A, inverse of `compile`); `C→A` is their composition; `dump_xml` is partial (raises on cyclic refs and non-null unions) |
