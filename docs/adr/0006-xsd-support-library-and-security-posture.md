# 0006: XSD Support — Library Choice, Security Posture, and Type Mapping

**Status:** Accepted

**Date:** 2026-05-28

**Authors:** Ben Lin, Claude Sonnet 4.6

## Context

weirding's primary authoring format is the plain-attribute annotation convention (ADR-0001).
XSD was explicitly rejected as the *primary* format: it is too verbose for LLM prompt
templates, and no maintained Python runtime XSD converter existed at ADR-0001 decision time.

However, XSD *input* support is a legitimate secondary need. Enterprise environments
frequently have existing XSD contracts (SOAP services, document interchange schemas,
regulatory definitions) that users want to compile into Pydantic models via weirding's
pipeline. Phase 03 adds `weirding[xsd]`, an optional extra that enables `compile()` to
accept XSD documents.

Three decisions had non-obvious rationale and required a record:

**1. Library selection.** Any XSD runtime implementation requires a library that can parse
and walk XSD schema components (complex types, element declarations, facets). The
constraints were:
- Must be a pure-Python dependency (no Rust/C extensions — see MEMORY.md rule 6)
- Must be actively maintained
- Must expose a component-level object model (not just validation), so we can walk types
  to produce JSON Schema IR
- Must support XSD 1.0 at minimum

Candidates surveyed:
- **`xmlschema`** (Davide Brunato, active since 2016, latest release 2024): pure Python,
  full XSD 1.0 and 1.1 support, rich component object model, `defuse` security parameter,
  active maintenance. The only viable candidate.
- **`lxml.etree`**: ships an XSD validator but exposes no component object model — cannot
  walk element declarations or type hierarchies programmatically.
- **`generateDS`** / **`pyxb`**: generate Python code from XSD at build time, not at
  runtime. Not applicable to a library that compiles XSD on-demand from user input.
- **`datamodel-code-generator`**: explicitly banned as a runtime dependency by MEMORY.md
  rule 7 (ruff subprocess startup cost, black cold start cost, Databricks binary
  compatibility risk).
- No other maintained Python runtime XSD parser exists.

**2. Security posture.** weirding receives XSD as arbitrary user-provided input. XSD
documents can reference external resources via `xs:import`, `xs:include`, and XML entity
declarations. An unrestricted parse can trigger:
- XXE (XML External Entity) injection — reading local files or making network requests
  through entity expansion
- SSRF (Server-Side Request Forgery) via `xs:import` resolving to attacker-controlled URLs
- Billion-laughs / quadratic blowup via entity nesting

The `xmlschema` library offers a `defuse` parameter with three levels:
- `"remote"` (default): blocks only remote resource fetching; local file resolution and
  entity expansion are permitted
- `"local"`: blocks remote and local file resolution; entity expansion permitted
- `"always"`: blocks all external resolution and entity expansion unconditionally

The decision was to use `defuse="always"` exclusively, not the default. The threat model
for weirding — a library that runs in Databricks, Kubernetes, and serverless environments
and processes user-provided XSD strings — requires zero external I/O on the schema parse
path. `defuse="remote"` would still permit local file reads, which is unacceptable when
weirding is deployed in a multi-tenant environment or receives schema content over a
network boundary.

Defense-in-depth: weirding's `make_parser()` (the lxml `XMLParser` with
`resolve_entities=False`, `no_network=True`, `load_dtd=False`, `huge_tree=False`) runs
first and produces the `lxml.etree._Element` that is passed to `XMLSchema(root, defuse="always")`.
The lxml layer prevents entity injection before `xmlschema` ever processes the input.
`defuse="always"` is a second independent layer ensuring `xmlschema`'s own resource
resolution logic is also disabled.

A consequence of `defuse="always"` is that multi-file XSD schemas using `xs:import` or
`xs:include` do not work. This is a deliberate scope limitation: weirding accepts XSD as
an in-memory string, not as a file path, so relative `xs:include` paths have no meaningful
resolution base anyway. Single-document self-contained XSDs are the supported scope.

**3. Type map key format.** When walking `xmlschema` type objects, type names are exposed
via `type_obj.name`. The value is a Clark-notation URI:
`{http://www.w3.org/2001/XMLSchema}string`. The `type_obj.prefixed_name` attribute
returns `xs:string`, but this prefix is the schema document's own declared prefix for the
XSD namespace — it could be `xsd:`, `x:`, or anything else the document author chose.
Using `prefixed_name` as a map key would fail silently for any schema that uses a
non-`xs` prefix for the XSD namespace.

## Decision

We will use `xmlschema>=3.0` as the sole XSD parsing and component-walking library,
scoped to the optional `weirding[xsd]` extra. It is never a base dependency.

Every call to `xmlschema.XMLSchema()` must pass `defuse="always"`. The default
(`defuse="remote"`) is never used in weirding code. This applies to all call sites in
`src/weirding/xsd/` and any future modules that invoke `xmlschema`.

The XSD type map (`_XSD_TYPE_MAP` in `src/weirding/xsd/_bridge.py`) uses Clark-notation
URI keys and is looked up via `type_obj.name`. The `prefixed_name` attribute is never used
for type dispatch.

The following are explicitly out of scope for the XSD bridge:
- `xs:import` and `xs:include` (blocked by `defuse="always"`)
- `xs:extension` / `xs:restriction` on complex content (inheritance chains)
- Multiple top-level element declarations (first declaration used as root)

## Consequences

### Positive

- `xmlschema` is the only maintained option; no meaningful library selection risk.
- `defuse="always"` + lxml `make_parser()` provides defense-in-depth against XXE, SSRF,
  and entity-expansion attacks on all code paths that process XSD input.
- Clark-notation keys in `_XSD_TYPE_MAP` make type dispatch correct regardless of the
  XSD namespace prefix the schema author chose.
- Scoping `xmlschema` to `[xsd]` keeps the base install footprint small; users who only
  use the plain-attribute annotation path do not pay the import cost.

### Negative

- Multi-file XSD schemas using `xs:import` or `xs:include` are not supported. Users with
  large enterprise XSD suites that split across files must pre-process (inline) the schema
  before passing it to `compile()`.
- `xmlschema` adds approximately 1–2 MB to the installed package size for `[xsd]` users.
- `xmlschema.XMLSchema(root, defuse="always")` performs full schema validation on every
  `compile()` call. For very large XSD files (thousands of type definitions), this may
  add noticeable latency. Applications that call `compile()` in a hot path should cache
  the result.
- Schema inheritance (`xs:extension`, `xs:restriction` on complex content) is not
  supported. Fields from base types will not appear in the produced IR.

### Neutral

- Any future code that calls `xmlschema.XMLSchema()` must pass `defuse="always"`. This is
  a permanent requirement, not a configuration choice.
- Any new XSD type mappings added to `_XSD_TYPE_MAP` must use Clark-notation URI keys.
- `xs:choice` model groups are supported and emit `oneOf`; `xs:sequence` and `xs:all` emit
  standard `properties`/`required` objects.
