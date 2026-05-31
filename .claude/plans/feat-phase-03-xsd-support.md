# Plan: pylance-zero-errors

**Branch:** feat/phase-03-xsd-support  
**Created:** 2026-05-31  
**Status:** COMPLETE

## Context

After updating project dependencies (`lxml-stubs>=0.5` added, pydantic bumped to `>=2.13.4`,
lxml to `>=6.1.1`), Pylance now surfaces type errors that were previously invisible. The project
has no `pyrightconfig.json`, no pyright in the quality gate, and no documented zero-Pylance-errors
convention. This plan resolves the current errors and institutionalizes the standard.

Research confirmed: `[tool.pyright]` in `pyproject.toml` (not a separate JSON file);
`typeCheckingMode = "standard"`; `reportMissingTypeStubs = "none"` globally; file-level
suppression in `_bridge.py`; `pyright` installed via the PyPI wrapper (`pyright-python`),
run via `uv run pyright`.

## Protected Files

| File | Tier | Expected change |
|------|------|-----------------|
| `src/weirding/__init__.py` | **Tier 1** | Line 195: `# type: ignore[arg-type]` → `# type: ignore` (drop mypy-specific error code suffix pyright does not recognize). One-line comment change only. |
| `src/weirding/_schema.py` | Tier 2 | Fix any errors surfaced by lxml-stubs 0.5 — expected minimal |
| `src/weirding/_models.py` | Tier 2 | Cast `create_model()` return; handle `model_config` ClassVar assignment |

## ADR Candidate

**ADR-0007: Type Checking Adoption** — trade-off decision: pyright over mypy; `standard`
mode over `strict`; global `reportMissingTypeStubs = "none"` with file-level suppression
in `_bridge.py`. Cross-component impact (quality gate, MEMORY.md rule, CLAUDE.md). Author
via `/adr` alongside or immediately after this implementation.

## Simplicity Challenge

Could this be one phase? Mechanically yes. Three phases are necessary because Phase 1
produces the actual pyright error list (unknown until the tool runs against the live code),
which drives what Phase 2 must fix. Speculative fixes in Phase 2 without a baseline risk
over-annotating. Phases 2 and 3 can be collapsed if the error count is small.

---

## Phase 1 — Baseline: Install pyright, capture current errors

**Goal:** Get pyright running; capture the real error list before touching any source.

**Files modified:**
- `pyproject.toml`
  - Add `pyright>=1.1.390,<2` to `[project.optional-dependencies] dev`
  - Add `[tool.pyright]` section:

```toml
[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.13"
venvPath = "."
venv = ".venv"
typeCheckingMode = "standard"
reportMissingTypeStubs = "none"
```

**Steps:**
1. Edit `pyproject.toml`
2. `uv sync --extra dev`
3. `uv run pyright` — capture and report full error list

**Completion signal:** pyright runs and produces output (exit code non-zero is expected and OK at this stage).

**Estimate:** 15 min

---

## Phase 2 — Fix type errors

**Goal:** Zero pyright errors.

**Files modified (in order of expected complexity):**

1. `src/weirding/xsd/_bridge.py`
   - Add file-level suppression at top of file:
     ```python
     # pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
     ```
   - Add explicit `Any` type annotations to all untyped parameters:
     `xsd_type`, `complex_type`, `choice_group`, `elem_decl` (all → `: Any`)
   - Import `from typing import Any` at top (already has `from __future__ import annotations`)

2. `src/weirding/_models.py` (Tier 2)
   - Check whether `json-schema-to-pydantic` ships a `py.typed` marker or inline stubs before deciding if `create_model()` return needs a `cast(type[BaseModel], ...)` or just `# type: ignore[no-untyped-call]`
   - Handle `model.model_config = ConfigDict(...)` ClassVar assignment with `# type: ignore[misc]` (preferred; simpler than `type.__setattr__()` and easier to grep)

3. `src/weirding/_serializers.py`
   - Verify `FieldInfo` from `pydantic.fields` is not flagged (pydantic ships `py.typed` + stubs; this import should be fine)
   - Verify match-statement type narrowing on `[*items]` pattern passes in standard mode

4. `src/weirding/_schema.py` (Tier 2)
   - Fix any lxml-stubs 0.5 issues with `etree._Element` (private type) — expected: add `# type: ignore` if stubs mark it as private-only

5. `src/weirding/__init__.py` (Tier 1, minimal)
   - Line 195: `# type: ignore[arg-type]` → `# type: ignore` (drop mypy error code suffix)

**Completion signal:** `uv run pyright` exits 0.

**Estimate:** 1–2 hours

---

## Phase 3 — Quality gate and documentation

**Goal:** Institutionalize zero-pyright-errors as a project standard.

**Files modified:**
- `CLAUDE.md`: Add `Type Check | uv run pyright` row to Commands table
- `.claude/memory/MEMORY.md`: Add rule 13: "Zero pyright errors — `uv run pyright` must exit 0 before every commit"; add note that pyright binary download required on first run — may fail in network-isolated CI (Phase 04 to address)

**Commit:**
```
chore(types): add pyright to dev deps and quality gate, fix all type errors

- Add pyright>=1.1.390,<2 to dev extra
- Add [tool.pyright] in pyproject.toml (standard mode, reportMissingTypeStubs=none)
- Add file-level suppression in xsd/_bridge.py for stub-less xmlschema
- Annotate all untyped bridge parameters as Any
- Fix model_config ClassVar assignment in _models.py
- Extend quality gate: uv run ruff check . && uv run pyright
- Update MEMORY.md with zero-pyright-errors rule

Co-Authored-By: Ben Lin <blin7.webdev@gmail.com>
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Completion signal:** `uv run pytest && uv run ruff check . && uv run pyright` all exit 0.

**Estimate:** 15 min

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| pyright reports more errors in `_models.py` than expected | Medium | `# type: ignore` per line; escalate to ADR if structural changes needed |
| `__init__.py` Tier 1 changes grow beyond comment fix | Low | Stop and get explicit approval for each additional change |
| `reportMissingTypeStubs = "none"` insufficient — xmlschema still errors | Medium | Add `reportUnknownParameterType = "none"` to `[tool.pyright]` as fallback |
| `model_config` ClassVar assignment requires structural refactor | Low | Use `type.__setattr__()` as type-safe workaround; document in code |
| Pyright version instability (pyright-python wrapper vs bundled engine) | Low | Pin `pyright>=1.1.390,<2` |

---

## Total Estimate

~2–2.5 hours across all three phases.
