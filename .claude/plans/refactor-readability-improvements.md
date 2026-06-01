# IMPLEMENTATION PLAN: readability-improvements

**Branch:** `refactor/readability-improvements`
**Date:** 2026-05-31
**Status:** COMPLETE — commit d5de677

## Context

weirding's pipeline transforms `xml: str|bytes` → `lxml._Element` → JSON Schema IR `dict`
→ `type[BaseModel]`. Every function that produces or consumes the JSON Schema IR currently
annotates it as bare `dict` or `dict[str, Any]`, making it invisible to both human readers
and static analysis that *this* dict is the canonical IR defined in ADR-0002.

Additional friction points:
- `xsd/_bridge.py` has `_type_to_ir()` and `_type_to_schema()` — similar names, identical
  `dict` return types, no name-readable distinction (one is a pure map lookup; the other is
  the general type dispatcher)
- `_serializers.py` hosts both `to_xml()` and `_xml_to_dict()` with no module-level signal
  of the dual (serialize + deserialize) responsibility

Research confirmed: `TypeAlias` from `typing` is the correct approach for Python 3.11+ with
pyright standard mode. `NewType` and `TypedDict` are both unsuitable for this open-ended
recursive dict (see ideation research finding). ADRs touched: ADR-0002, ADR-0007.

---

## Phase 1 — Foundation: `_types.py` + non-protected internal modules

**Files created:**
- `src/weirding/_types.py`

**Files modified:**
- `src/weirding/_schema.py`
- `src/weirding/_models.py`

**Protected files:** none

**Changes:**

`_types.py` (note: deliberately NO `from __future__ import annotations` — this module
exists solely to declare aliases; deferring annotations here is a footgun for future
maintainers who follow the project-wide pattern without understanding the exception):
```python
from typing import Any, TypeAlias

JsonSchemaIR: TypeAlias = dict[str, Any]
```

`_schema.py`: import `JsonSchemaIR`; update return type of `_element_to_schema()` and
`compile_schema()`. The `_apply_attrs(element, schema: dict[str, Any])` in-place mutator
parameter stays as `dict[str, Any]` — it mutates a fragment, not a complete IR.

`_models.py`: import `JsonSchemaIR`; update the `schema` parameter of `build_model()`.

**Completion signal:** `uv run pyright` exits 0 with zero new errors on all modified files.

**Estimate:** 30 min

---

## Phase 2 — XSD bridge (Tier 2 protected file)

**Files modified:**
- `src/weirding/xsd/_bridge.py` (Tier 2)

**Protected files:** `_bridge.py` (Tier 2 — explanation required; approval not required)

**Tier 2 explanation:** Changes are purely additive type annotations and one function
rename. No logic changes, no IR structure changes. The existing file-level pyright
directive (`reportUnknownMemberType=false` etc.) remains. ADR-0007 explicitly requires
type checking in this module; these changes strengthen that coverage.

**Changes:**

1. Import `JsonSchemaIR` and apply to all bridge function return annotations.

2. Rename `_type_to_ir` → `_primitive_to_ir`:
   - `_type_to_ir` is a pure map-lookup against `_XSD_TYPE_MAP` — not a full type
     conversion. Its name was indistinguishable from `_type_to_schema` (the general
     dispatcher). The new name signals "this only handles primitives in the type map."
   - The bridge has 3 call sites (2 in `_type_to_schema`, 1 in `_complex_type_to_ir`);
     grep the file to confirm all are updated rather than counting from the plan.

3. All bridge functions annotated `-> JsonSchemaIR`:
   `_primitive_to_ir`, `_type_to_schema`, `_choice_to_ir`, `_complex_type_to_ir`,
   `_elem_decl_to_ir`, `xsd_to_ir`

4. Update `_XSD_TYPE_MAP` annotation from `dict[str, dict]` → `dict[str, JsonSchemaIR]`
   (line 34 of current `_bridge.py` — the most frequently accessed IR source in the
   module; leaving it as `dict[str, dict]` after Phase 2 would be an inconsistency that
   directly undermines the plan's readability goal)

**Completion signal:** `uv run pyright` exits 0; `ruff check src/weirding/xsd/` clean;
`grep -r "_type_to_ir" src/` returns zero results.

**Estimate:** 30 min

---

## Phase 3 — Public API surface + `_serializers.py` intent signal (Tier 1)

**Files modified:**
- `src/weirding/__init__.py` (Tier 1)
- `src/weirding/_serializers.py`

**Protected files:** `__init__.py` (Tier 1 — approved via user PROCEED on this plan)

**Tier 1 justification:** All changes in `__init__.py` are additive. `JsonSchemaIR`
is `dict[str, Any]` — pyright treats the alias transparently; all existing callers
continue to compile without modification.

Changes in `__init__.py`:
1. Add `from weirding._types import JsonSchemaIR`
2. Add `"JsonSchemaIR"` to `__all__` — callers may annotate `schema: weirding.JsonSchemaIR`
3. `compile(xml: str | bytes) -> dict` → `-> JsonSchemaIR`
4. `from_schema(schema: dict, ...)` → `schema: JsonSchemaIR`
5. `DTOBuilder.build(self, schema: dict, ...)` → `schema: JsonSchemaIR`

Changes in `_serializers.py`:
- Add module docstring: `"""XML ↔ Python object codecs: to_xml (serialize) and _xml_to_dict (deserialize)."""`
- Rename `_xml_to_dict(element, model_type)` parameter: `model_type` → `model_cls`
  (removes `-type` suffix that implies validation; the function does structural field
  introspection, not validation — the docstring already says so; the parameter name
  reinforces it)
- Module is NOT renamed — `_serializers` (plural) is valid; the docstring signals dual
  responsibility without touching import sites

**Completion signal:** `uv run pyright` exits 0; `"JsonSchemaIR"` in `weirding.__all__`;
`python -c "import weirding; print(weirding.JsonSchemaIR)"` prints `dict[str, typing.Any]`.
(Note: `compile.__annotations__["return"]` will be the string `"JsonSchemaIR"` at runtime
due to `from __future__ import annotations` in `__init__.py` — the pyright check is the
authoritative signal, not runtime annotation inspection.)

**Estimate:** 30 min

---

## Phase 4 — Full quality gate

**Files created/modified:** none

**Actions:**
1. `uv run pyright`
2. `uv run pytest`
3. `uv run ruff check .`
4. `uv run ruff format --check .`

**Completion signal:** All four commands exit 0.

**Estimate:** 10 min

---

## ADR Candidates

- **`JsonSchemaIR` exported from `weirding.__all__`** — Extends the public API surface.
  Consistent with ADR-0002 (the IR is the public API contract). Decision: export it.
  Not large enough for a full ADR; update MEMORY.md under Confirmed Standards instead.

---

## Protected Files Requiring Approval

| File | Tier | Change | Approval |
|------|------|--------|----------|
| `src/weirding/__init__.py` | Tier 1 | Add `JsonSchemaIR` to `__all__`; update 3 annotation sites | Approved via user PROCEED |
| `src/weirding/xsd/_bridge.py` | Tier 2 | Annotation updates + rename `_type_to_ir` | Explanation provided above |

---

## Simplicity Check

**Considered and rejected:**

- **Splitting `_serializers.py`** into `_serializer.py` + `_deserializer.py`: Would update
  3 import sites including Tier 1 `__init__.py`. A module docstring achieves the same
  readability intent with zero refactoring surface. Rejected.
- **Renaming `_serializers.py` to `_codecs.py`**: Same tradeoff. Rejected.
- **Collapsing `_primitive_to_ir` inline**: Two call sites would each duplicate the default
  sentinel `{"type": "string"}` and obscure the type-map-lookup pattern. Rejected.
- **Three phases**: Phases 1+2 could merge since neither touches Tier 1. Kept separate
  because Phase 2 has a distinct reviewable action (the rename) and a Tier 2 protected
  file — a separate phase makes the agent pause to verify the rename is complete.
