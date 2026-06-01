# 0007: Type Checking Adoption — pyright, standard mode, suppression scope

**Status:** Accepted

**Date:** 2026-05-31

**Authors:** Ben Lin

## Context

weirding is a production-grade Python library that ships a `py.typed` marker and intends
to be used by callers who rely on type information. Despite this, the project had no type
checker in its quality gate. The issue surfaced when `lxml-stubs>=0.5` was added to the
dev dependencies as part of a routine dependency update: Pylance (Microsoft's Python
language server, powered by pyright) immediately began reporting type errors that had been
invisible before. The project needed a type-checking standard before Phase 04 (Distribution)
could be considered complete.

### Constraints

- The project uses `uv` for dependency management with a `src/weirding/` layout.
- Four runtime dependencies exist: `pydantic`, `lxml`, `json-schema-to-pydantic`, and
  (optionally, in `[xsd]`) `xmlschema`. Of these:
  - `pydantic` ships `py.typed` and full inline stubs — fully typed.
  - `lxml` has no `py.typed` but has a separate `lxml-stubs` package (already a dev dep) — fully typed via stubs.
  - `json-schema-to-pydantic` ships no `py.typed` and no PyPI stub package — untyped.
  - `xmlschema` ships no `py.typed` and no PyPI stub package — untyped.
- The XSD bridge module (`src/weirding/xsd/_bridge.py`) is the only module that imports
  from stub-less libraries at the top level. All other modules call into typed code.
- A zero-warnings policy is enforced on every build. Any type checker configuration that
  floods the output with warnings from third-party libraries would violate this policy
  before any project code could be fixed.

### Alternatives considered

**Alternative 1 — mypy**

mypy is the older, more widely deployed Python type checker. It is used in many
production Python libraries. However:
- mypy and pyright use different error models and different resolution of ambiguous cases.
  Running both would produce conflicting requirements and conflicting suppression
  annotations.
- Pylance (the default VS Code Python extension) is powered by pyright, not mypy. A
  mypy-only gate would leave Pylance errors invisible in CI while appearing in the editor —
  the opposite of the desired effect.
- mypy's handling of `lxml-stubs` is less complete than pyright's.

**Alternative 2 — pyright strict mode**

`typeCheckingMode = "strict"` enables all pyright checks including
`reportUnknownMemberType`, `reportUnknownParameterType`, and `reportMissingParameterType`.
In strict mode, every call site into an untyped library (`xmlschema`, `json-schema-to-pydantic`)
emits an error because the return types are `Unknown`. A test run on this project produced
26+ errors from third-party call sites in `_bridge.py` alone, none of which are actionable
without re-typing the third-party objects. Strict mode is a valid long-term target but
requires either (a) complete inline stubs for all dependencies or (b) accepting hundreds
of per-site `# type: ignore` annotations that would obscure real project-owned errors.

**Alternative 3 — exclude `src/weirding/xsd/` from type checking entirely**

Excluding the XSD bridge from analysis would silence all xmlschema-related errors. This
was rejected because the bridge contains non-trivial type dispatch logic
(`_type_to_schema`, `_complex_type_to_ir`, `_elem_decl_to_ir`) where wrong return types
would silently produce invalid IR dicts. The bridge is exactly where type checking
provides value — excluding it defeats the purpose.

**Alternative 4 — per-file `pyrightconfig.json` overrides**

pyright allows per-directory configuration via nested `pyrightconfig.json` files. This
would allow strict mode in `src/weirding/` and disabled mode in `src/weirding/xsd/`.
Rejected because: (a) per-directory config files are a maintenance burden; (b) a
`pyrightconfig.json` at the repo root silently overrides `[tool.pyright]` in
`pyproject.toml`, creating a footgun for future contributors who add the JSON file.

## Decision

We will use **pyright** (via the `pyright` PyPI package, which wraps the pyright Node
binary) as the sole type checker for this project, configured in `[tool.pyright]` in
`pyproject.toml` with `typeCheckingMode = "standard"`.

**Configuration:**

```toml
[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.13"
venvPath = "."
venv = ".venv"
typeCheckingMode = "standard"
reportMissingTypeStubs = "none"
```

`reportMissingTypeStubs = "none"` globally suppresses the missing-stubs warning for
`xmlschema` and `json-schema-to-pydantic`. This is a global suppression rather than a
per-module override because both stub-less libraries are only called from within
`src/weirding/xsd/_bridge.py` and `src/weirding/_models.py` respectively, and the
file-level suppression in `_bridge.py` (see below) provides the narrower scope where
needed.

`_bridge.py` carries a file-level pyright directive:

```python
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
```

This limits the broader suppression to the one module that interfaces with a stub-less
library. All other source files retain full `standard`-mode checking.

**What was explicitly rejected:**

- mypy — wrong tool for a project targeting Pylance/VS Code users.
- strict mode — not actionable with current stub coverage of dependencies; deferred.
- Excluding `src/weirding/xsd/` — defeats the purpose; bridge logic is type-checked.
- `pyrightconfig.json` as a separate file — creates a silent-override footgun.

**Preconditions for this decision to remain valid:**

If `xmlschema` or `json-schema-to-pydantic` publish official `py.typed` markers or PyPI
stub packages in the future, the global `reportMissingTypeStubs = "none"` suppression
should be narrowed or removed. Monitor their release notes.

If the project later adopts strict mode (a valid evolution), `_bridge.py` will require
explicit `Any`-typed parameters on all bridge functions (already in place as of this ADR)
plus removal of the file-level directive.

## Consequences

### Positive

- `uv run pyright` exits 0 on `src/` and `tests/` — type errors are caught at CI time,
  not discovered by callers after release.
- Pylance errors in VS Code match CI results — the same engine (pyright) runs in both
  contexts. Developers get accurate inline type feedback.
- lxml usage is fully type-checked via `lxml-stubs`. Incorrect `etree._Element` handling
  will be caught at development time.
- The `from_schema()` overload signatures now correctly express the `builder=None →
  type[BaseModel]` case, giving callers accurate return-type inference without needing
  explicit casts.
- Zero-warning policy is extended to cover type errors, not just lint.

### Negative

- `pyright>=1.1.390,<2` downloads its Node binary on first run (pyright-python wrapper).
  This will fail silently in network-isolated CI environments. Phase 04 CI/CD
  configuration must either pre-cache the binary or verify network access.
- `typeCheckingMode = "standard"` is not `"strict"`. The following error categories are
  not caught: `reportUnknownParameterType` on internal helper functions, complete
  `reportMissingParameterType` enforcement. These represent real type gaps in the codebase
  that will not be flagged until strictness is raised.
- Adding pyright to the quality gate increases the gate runtime by ~5–10 seconds on a
  cold start (binary download aside). Warm runs are under 2 seconds.
- `# type: ignore` comments in the codebase use plain form (no error-code suffix). Pyright
  will emit a warning if a `# type: ignore` comment covers no actual error at that site —
  these must be reviewed if surrounding code changes.

### Neutral

- mypy is not configured and not planned. If a future contributor adds mypy, they will
  need to audit the `# type: ignore` annotations for compatibility (mypy uses different
  error codes).
- `json-schema-to-pydantic` was confirmed to ship no `py.typed` or stubs. `create_model()`
  returns `Unknown`. This is handled in `_models.py` by relying on pyright's `standard`
  mode treating `Unknown` permissively at assignment. If stubs are added upstream, the
  assignment may gain an explicit `cast()`.
- The `pythonVersion = "3.13"` in `[tool.pyright]` reflects the actual venv version. The
  package `requires-python = ">=3.11"` — if a contributor runs with 3.11 or 3.12, the
  venv will differ and pyright may report stdlib-version-specific false positives. The
  canonical development environment is Python 3.13.
