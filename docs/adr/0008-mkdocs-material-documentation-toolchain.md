# 0008: MkDocs + Material Documentation Toolchain

**Status:** Accepted

**Date:** 2026-06-01

**Authors:** Ben Lin

## Context

weirding's Phase 04 distribution target (PyPI) requires user-facing documentation beyond
the repository README. The library exposes a public API (`compile`, `define_model`,
`from_schema`, `parse`, `to_xml`, `prompt.*`, and several Protocols/types) that callers
need to discover, with docstrings already written in Google style. The documentation
system must:

1. Render Markdown natively — the project's governing files are already in Markdown
2. Auto-generate API reference from Python docstrings without a separate build step
3. Correctly handle `from __future__ import annotations` and `@overload` in API modules —
   a common failure mode in Python documentation tooling
4. Require no Google Fonts or external CDN resources (ETHOS.md privacy constraint:
   "No third-party requests from the UI")
5. Be deployable to GitHub Pages via a single CLI command

### Alternatives considered

**Sphinx + autodoc + furo/pydata themes**

Sphinx is the traditional Python documentation system. It offers the richest ecosystem and
the widest theme selection. However:
- Sphinx requires reStructuredText (`.rst`) by default; Markdown support via MyST adds
  configuration overhead
- The Sphinx build model is significantly more complex (conf.py, multiple Sphinx
  extensions, intersphinx, etc.)
- Cold build times are longer than MkDocs for small-to-medium projects

Not selected: unnecessary complexity for a library at weirding's current scale, and RST
diverges from the project's all-Markdown convention.

**pdoc**

pdoc generates single-page or per-module API documentation directly from docstrings with
zero configuration. It is the simplest option.

Not selected: pdoc produces API-only documentation with no room for prose guides, and its
single-page output is unsuitable for the Getting Started + API Reference + ADR nav
structure the project requires.

**README-only (no docs site)**

Keep documentation in `README.md` and point PyPI users there.

Not selected: the full Getting Started guide, LLM retry workflow, and API reference would
make the README unwieldy. A docs site also enables versioning via GitHub Pages.

**MkDocs + mkdocstrings-python (Griffe)**

mkdocstrings uses Griffe as its Python AST parser. Griffe correctly handles:
- `from __future__ import annotations` (deferred annotation evaluation, used project-wide)
- `@overload` stubs for `from_schema()`
- Google-style docstrings (the project convention, per MEMORY.md)

Production reference: pydantic, httpx, and fastapi all use MkDocs + mkdocstrings for
their documentation sites.

### Maintenance posture of Material for MkDocs 9.x

Material for MkDocs 9.7 entered maintenance mode in November 2025. The maintainer
(Zensical) has committed to security fixes through November 2026. A next-generation
successor (currently referred to as MkDocs 2.0) is under development; however, as of
June 2026 it has no migration path and is unlicensed for production use. Material 9.7
is the correct choice for a new project today: it is stable, widely deployed, and the
migration risk is low given weirding's minimal theme customization.

## Decision

We will use **MkDocs 1.6 + Material 9.7 + mkdocstrings-python** as the documentation
toolchain, pinned as an optional `[docs]` dependency group:

```toml
docs = [
    "mkdocs-material>=9.7,<10",
    "mkdocstrings[python]>=0.28",
]
```

`theme.font: false` is set in `mkdocs.yml` to disable Google Fonts injection, satisfying
the ETHOS.md "no third-party requests from the UI" constraint.

Sphinx was explicitly rejected as too heavyweight for current scale. pdoc was rejected as
insufficient for multi-section navigation. README-only was rejected as incompatible with
the Phase 04 distribution quality bar.

This decision applies to the `docs/` site only. Internal project documents (ADRs,
planning, MEMORY.md) remain Markdown files and are not part of the docs build nav.

## Consequences

### Positive

- `uv run mkdocs build --strict` is the docs completion signal — zero-warning policy
  applies to docs builds
- `uv run mkdocs gh-deploy` deploys to GitHub Pages in Phase 04 CI with no additional
  tooling
- API reference is automatically kept in sync with docstrings — no manual maintenance
- Material 9.7 is stable and widely understood; onboarding friction is low
- Google Fonts disabled at config level — no future contributor can accidentally enable it

### Negative

- Adds `[docs]` optional dep group (~40 MB installed); not installed in the default
  `pip install weirding` user path
- Material 9.7 maintenance window ends November 2026; migration to next-generation
  toolchain will be required before or at that date
- Griffe's handling of complex generic types may require explicit type annotations in
  some edge cases

### Neutral

- `site/` directory is already in `.gitignore` (the standard MkDocs output path)
- Phase 04 CI/CD configuration must install `weirding[docs]` separately from `weirding[dev]`
- Any future significant theme customization that diverges from Material defaults will
  increase the migration cost to the next-generation toolchain
