# Plan: Pre-Release Documentation and Test Quality

**Branch:** main (create `docs/pre-release-docs-and-pbt` before implementing)
**Phase context:** Phase 03 complete; Phase 04 (Distribution) in progress  
**Created:** 2026-06-01  
**Depends on:** `chore/pre-release-standards-hardening` merged to main first (adds ruff D rules, coverage threshold, 9 MEMORY.md standards)

---

## Goal

Deliver the documentation and test quality work identified in the ideation's Track 2:
- Complete README Getting Started with a working, copy-paste example
- Replace the Melange template CHANGELOG with weirding-specific release history
- Set up MkDocs + Material documentation site (API reference + Getting Started)
- Add Hypothesis property-based tests for IR well-formedness and round-trip identity

No protected files are touched. No behavior changes to library code.

---

## Simplicity Challenge

Could this be one phase? The docs setup (Phase 1) and the Hypothesis suite (Phase 2) are
genuinely independent — each has its own completion signal, its own dependency additions, and
its own test feedback loop. Merging them means a single agent session that mixes `mkdocs build`
failures (docs tooling) with `pytest` failures (PBT strategy bugs). Keeping them separate is
cleaner iteration.

Could this be three phases? Splitting CHANGELOG out of Phase 1 would create a 5-minute commit
with no build impact — unnecessary. CHANGELOG, README, and MkDocs all live in the same
documentation pass and commit together naturally.

---

## Protected Files

None. This plan creates new files and edits non-protected files only:
- `pyproject.toml` — dependency additions (docs and hypothesis extras)
- `CHANGELOG.md` — full replacement of template content
- `README.md` — replace Getting Started placeholder with functional example
- `mkdocs.yml` — new file (project root)
- `docs/index.md` — new file
- `docs/api.md` — new file
- `tests/test_schema_pbt.py` — new file
- `.hypothesis/` — new directory (committed, small)

---

## ADR Candidates

**ADR required — MkDocs + Material toolchain (Phase 1):** Trade-off between MkDocs
Material (markdown-native, fast) vs. Sphinx (RST-default, more extensible, larger ecosystem).
Cross-component impact: adds new `[docs]` optional dep group, new root `mkdocs.yml` config,
and a CI build step. Hard to reverse once a public docs URL is established. The implementing
agent must author this ADR after `mkdocs build --strict` passes — do not defer to MEMORY.md.

---

## Phase 1 — Documentation Site and CHANGELOG

**Goal:** Complete the README Getting Started, replace the template CHANGELOG, configure
MkDocs, and verify the docs site builds cleanly.

**Files created:**
- `mkdocs.yml` (project root)
- `docs/index.md`
- `docs/api.md`

**Files modified:**
- `pyproject.toml` — add `docs` optional-dependency group
- `README.md` — replace Getting Started placeholder
- `CHANGELOG.md` — full replacement of Melange template with weirding history

**Protected files:** none

### 1.1 — Add docs dependencies to `pyproject.toml`

Add a `docs` optional-dependency group:
```toml
[project.optional-dependencies]
docs = [
    "mkdocs-material>=9.7,<10",
    "mkdocstrings[python]>=0.28",
]
```

Run `uv sync --extra docs` to verify resolution.

### 1.2 — Create `mkdocs.yml`

```yaml
site_name: weirding
site_description: XML ↔ Pydantic v2 conversion for structured AI output workflows
repo_url: https://github.com/yogs0ddhoth/weirding

theme:
  name: material
  palette:
    - scheme: default
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      toggle:
        icon: material/brightness-4
        name: Switch to light mode

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            show_root_heading: true
            docstring_style: google

nav:
  - Getting Started: index.md
  - API Reference: api.md
  - Architecture Decisions: adr/README.md
```

Note: `docs/planning/` is intentionally excluded from the nav (internal tool, not user-facing).

### 1.3 — Create `docs/index.md` (Getting Started)

Write a complete, self-contained Getting Started guide covering:

1. **Installation** — `pip install weirding` and `pip install weirding[xsd]`
2. **Core workflow** — `compile()`, `define_model()`, `parse()`, `to_xml()` with working examples
3. **LLM retry workflow** — `RetryContext` + `to_template()` + `format_error()` with a realistic example

The example must be copy-paste runnable with no external dependencies beyond `weirding` itself.

Example structure for the core workflow section:
```python
import weirding

# Define a schema as annotated XML
schema_xml = """
<Response>
  <name type="string" required="true" description="The person's full name"/>
  <age type="integer" required="true" minimum="0"/>
  <bio type="string" required="false"/>
</Response>
"""

# Compile to JSON Schema IR (publicly exposed, cacheable)
ir = weirding.compile(schema_xml)

# Build a Pydantic model
Model = weirding.define_model(schema_xml)

# Parse XML (e.g., from an LLM response)
instance = weirding.parse("""
<Response>
  <name>Alice Smith</name>
  <age>30</age>
</Response>
""", Model)

# Round-trip back to XML
xml_string = weirding.to_xml(instance)

# Generate a prompt template for the schema
template = weirding.prompt.to_template(Model)
```

### 1.4 — Create `docs/api.md` (API Reference)

Use mkdocstrings `:::` directives to generate API reference from docstrings:

```markdown
# API Reference

## Core pipeline

::: weirding
    options:
      members:
        - compile
        - define_model
        - from_schema
        - parse
        - to_xml

## Prompt utilities

::: weirding.prompt
    options:
      members:
        - to_template
        - format_error
        - RetryContext

## Protocols and types

::: weirding
    options:
      members:
        - JsonSchemaIR
        - DTOBuilder
        - PydanticBuilder
        - Validatable

## Exceptions

::: weirding
    options:
      members:
        - WeirdingError
        - SchemaError
        - ParseError
        - UnsupportedDialectError
```

### 1.5 — Update `README.md` Getting Started

Replace the `_Getting Started instructions coming soon._` placeholder with a short
functional example (3–5 lines: install, `compile`, `define_model`, `parse`). The README is
the PyPI first-contact surface — keep it concise. Direct readers to the docs site for the
full guide.

### 1.6 — Replace `CHANGELOG.md`

Clear the Melange template content entirely. Write weirding-specific release history based
on the commit log (`git log --oneline`). Use Keep a Changelog format:

```markdown
# Changelog

All notable changes to weirding will be documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Added
- ruff D rules with Google docstring convention enforced across src/
- Coverage threshold (--cov-fail-under=90) gated in CI
- json-schema-to-pydantic pin tightened to >=0.4.7,<1
- 9 confirmed standards added to project memory (async policy, logging policy,
  IR semver contract, PBT file separation, dependency pinning strategy, and more)

## [0.1.0] — 2026-04-30

### Added
- `compile(xml)` — XML schema → JSON Schema IR dict (plain-attribute annotation dialect)
- `define_model(xml)` — XML schema → Pydantic v2 BaseModel (convenience wrapper)
- `from_schema(ir, name, builder)` — JSON Schema IR → Pydantic model (direct IR path)
- `parse(xml, model)` — XML data → validated Pydantic instance
- `to_xml(instance)` — Pydantic instance → XML string (round-trip serialization)
- `prompt.to_template(model)` — Pydantic model → XML prompt template for LLM structured output
- `prompt.format_error(error, model)` — ValidationError → human-readable retry message (no PII echoed)
- `prompt.RetryContext` — stateful retry loop helper for LLM workflows
- `DTOBuilder` Protocol — extensible model-building backend interface
- `PydanticBuilder` — default DTOBuilder backed by json-schema-to-pydantic
- `Validatable` Protocol — validation backend abstraction for parse()
- `JsonSchemaIR` — public TypeAlias for the JSON Schema IR dict
- `weirding[xsd]` optional extra — XSD schema support via xmlschema bridge
- XSD dialect auto-detected from root element tag
- Secure XML parsing (resolve_entities=False, no_network=True, load_dtd=False)
- XXE and billion-laughs attack prevention verified by security tests
```

Populate the [Unreleased] section from the `chore/pre-release-standards-hardening` commits
(the hardening work will land before this PR merges).

### 1.7 — Build and verify docs site

Run `uv run mkdocs build --strict` (the `--strict` flag treats warnings as errors, consistent
with the zero-warning policy). If the build emits warnings about unresolved references or
missing members, fix them.

**Completion signal:**
- `uv run mkdocs build --strict` exits 0
- `uv run ruff check . && uv run pyright && uv run pytest` all exit 0

**Commit:** `docs(site): add MkDocs site, Getting Started, API reference, and weirding CHANGELOG`

**Estimate:** 2–2.5 hours

---

## Phase 2 — Hypothesis Property-Based Tests

**Goal:** Add a Hypothesis test suite covering IR structural well-formedness and
the round-trip identity property.

**Files created:**
- `tests/test_schema_pbt.py`
- `.hypothesis/` directory (committed; empty initially, populated after first run)

**Files modified:**
- `pyproject.toml` — add `hypothesis` to `dev` optional deps, add `[tool.hypothesis]` section

**Protected files:** none

### 2.1 — Add hypothesis dependency

In `pyproject.toml`, add `hypothesis>=6.100` to the `dev` extra:
```toml
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "hypothesis>=6.100",
    "ruff>=0.15.15",
    "lxml-stubs>=0.5",
    "weirding[xsd]",
    "pyright>=1.1.390,<2",
]
```

Add `[tool.hypothesis]` section:
```toml
[tool.hypothesis]
# Hypothesis auto-detects the CI env var — no explicit profile config needed here.
# Per-profile settings (if needed) belong in conftest.py, not pyproject.toml.
```

Note: `deriving = ["ci"]` is NOT a valid Hypothesis TOML key and will cause a startup
warning/error. Hypothesis detects `CI=true` automatically and applies conservative settings.
No additional TOML configuration is required.

Run `uv sync --extra dev` to verify.

### 2.2 — Create `tests/test_schema_pbt.py`

Implement two property families per the MEMORY.md PBT standard and the ideation research:

**Property 1 — IR structural well-formedness**

For any valid weirding-annotation XML tree, `compile()` must return an IR dict that:
- Has `"type": "object"` at root
- Has `"title"` equal to the root tag name
- Has `"properties"` (a dict) and `"required"` (a list)
- Never contains `"prefixItems"` anywhere (MEMORY.md rule 11)

Strategy: `xml_schema_tree()` drawing from the attribute vocabulary (type from
`["string", "integer", "number", "boolean"]`, optional `required="false"`, basic
constraints). Keep nesting depth at 0 (flat schema) for this property — recursive schemas
are deferred to a post-v0.1 expansion.

**Tag name constraint (required):** XML element names must be legal NCNames — they cannot
start with a digit or contain spaces/metacharacters. Use
`st.from_regex(r'[A-Za-z_][A-Za-z0-9_]{0,19}', fullmatch=True)` for all element tag names
(both root tag and field names). Unrestricted `st.text()` will produce
`lxml.etree.XMLSyntaxError` at strategy time rather than a test failure, violating the
zero-warning policy.

Settings: `@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])`

**Property 2 — Round-trip identity**

For any schema that compiles without error and produces a model, and any valid data instance
for that schema: `parse(to_xml(instance), Model).model_dump() == instance.model_dump()`.

Strategy: `schema_and_valid_data()` — a composite strategy that generates both schema XML
and a valid data XML in the same `draw()` call, ensuring the data is always type-consistent
with the schema. This avoids the `hypothesis-jsonschema` compatibility concern (noted in
ideation research) by keeping data generation entirely in-process.

Data generation rules:
- `type="string"` fields: `st.text(alphabet=st.characters(whitelist_categories=['L', 'N', 'Zs']), max_size=20)`
- `type="integer"` fields: `st.integers(min_value=0, max_value=10000)`
- `type="number"` fields: `st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False)`
- `type="boolean"` fields: `st.booleans()` → `"true"` / `"false"` text content
- All required fields (no `required="false"`) are always included in data

Settings: `@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])`

### 2.3 — Commit `.hypothesis/` directory

After a successful `uv run pytest tests/test_schema_pbt.py` run, the `.hypothesis/` directory
is populated with a database of examples (typically <5 KB). Commit it:
```
git add .hypothesis/
```

Per the MEMORY.md PBT standard, committing `.hypothesis/` enables CI to replay shrunk
failures that were found locally without needing to rediscover them.

Add `.hypothesis/` to the `.gitignore` exclusion list if it's already there; remove the
exclusion so the directory is tracked.

### 2.4 — Verify no regressions

Run `uv run pytest` (full suite, including new PBT tests). Report:
- Total tests passing (should be 137 deterministic + new PBT tests)
- Coverage (should remain ≥90%)

**Completion signal:**
- `uv run pytest` exits 0
- `uv run ruff check . && uv run pyright` exit 0
- PBT tests complete within a reasonable time (under 60 seconds on warm Hypothesis DB)

**Commit:** `test(pbt): add Hypothesis property tests for IR well-formedness and round-trip identity`

**Estimate:** 2 hours

---

## Total Estimate: ~4.5 hours

---

## Post-Completion Checklist

- [ ] `uv run mkdocs build --strict` — site builds cleanly
- [ ] `uv run ruff check .` — zero violations
- [ ] `uv run pyright` — zero errors
- [ ] `uv run pytest --cov=weirding` — all tests pass, coverage ≥90%
- [ ] `CHANGELOG.md` contains weirding history (not Melange template)
- [ ] `README.md` Getting Started section is functional (not a placeholder)
- [ ] `docs/index.md` and `docs/api.md` exist
- [ ] `tests/test_schema_pbt.py` contains both property families
- [ ] `.hypothesis/` committed
- [ ] `docs/planning/` excluded from MkDocs nav (internal only)
- [ ] PR against `main` (depends on `chore/pre-release-standards-hardening` landing first)
