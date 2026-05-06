# Plan: Phase 00 Close-out + Phase 01 Core Pipeline

Planner verdict: **PROCEED WITH MODIFICATIONS** (incorporated below)

Approved modification: pipeline is XML → JSON IR → Protocol[DTOBuilder] → type[T],
not XML → JSON IR → Pydantic specifically. `from_schema()` accepts a pluggable
`DTOBuilder` Protocol. Default builder uses Pydantic. parse() already uses `Validatable`
Protocol — the consumption side is symmetrically backend-neutral.

---

## Pre-flight: Phase 00 close-out

### Step 0a — Roadmap correction
File: `docs/planning/PROJECT_ROADMAP.md`
- Phase 01: replace "r: namespace parser" → "plain-attribute annotation compiler (ADR-0001)"
- Move `parse()` from Phase 02 into Phase 01
- Phase 02 becomes: Prompt Utilities only (`to_template`, `format_error`, `RetryContext`)
- Update Current Focus: Phase 01
- Update Recently Completed: Phase 00 — Foundation

### Step 0b — MEMORY.md update
File: `.claude/memory/MEMORY.md`
- Mark ADR-0001 as Accepted with canonical attribute vocabulary
- Update Directory Layout Notes: add `_serializers.py` entry; note `DTOBuilder` in `__init__.py`
- Remove "ADR-0001 pending" language from Confirmed Standards
- Add `DTOBuilder` Protocol to confirmed public API surface

### Step 0c — Remove unused dep
File: `pyproject.toml`
- Remove `deepdiff>=8.0` from `[project.optional-dependencies.dev]`

### Step 0d — Commit
Commit all staged changes + 0a–0c fixes.

---

## Phase 01: Core Pipeline

### Step 1a — Annotation compiler
File: `src/weirding/_schema.py` (Tier 2 protected)

Implement `compile_schema(xml: str | bytes) -> dict`.

Logic:
1. Parse with `make_parser()` from `_parser.py`
2. Detect XSD root (`{http://www.w3.org/2001/XMLSchema}schema`) → `UnsupportedDialectError`
3. Walk element tree recursively:
   - Root → `{"type": "object", "title": <root_tag>, "properties": {...}, "required": [...]}`
   - Leaf → scalar from `type` attribute (default `"string"`)
   - Element with children, no explicit type → `type="object"`, recurse
   - `type="array"` → `{"type": "array", "items": <child schema>, "x-weirding-item-tag": <child_tag>}`
4. Attribute dispatch: `type`, `required` (default `"true"`), `description`, `enum` (pipe-split),
   `pattern`, `minimum`, `maximum`, `min`→`minLength/minItems`, `max`→`maxLength/maxItems`, `default`
5. `nullable="true"` → `{"anyOf": [{"type": T}, {"type": "null"}]}` (draft 2020-12)
6. Never emit `prefixItems`

Tests: `tests/test_schema.py`
- Scalar, object inference, array with `x-weirding-item-tag`, optional, enum (pipe-split),
  nullable (exact `anyOf` shape asserted), pattern/min/max, XSD → `UnsupportedDialectError`,
  malformed → `ParseError`

Completion signal: `pytest tests/test_schema.py -v` pass, lint clean
Estimate: M (1–2 days)

---

### Step 1a.5 — ADR-0005: x-weirding-item-tag
Author before Step 1c begins. Decision: keep `x-weirding-item-tag` in the IR as a
JSON Schema `x-*` extension key (compliant; standard consumers tolerate unknown keys).
Rejected: runtime singularization (breaks irregular plurals), strip-and-store-in-model
(splits self-contained IR).

---

### Step 1b — DTO builder abstraction + Pydantic builder
Files: `src/weirding/_models.py` (Tier 2), `src/weirding/__init__.py` (Tier 1, flagged)

**`DTOBuilder` Protocol** (defined in `__init__.py`, exported):
```python
@runtime_checkable
class DTOBuilder(Protocol):
    def build(self, schema: dict, *, name: str) -> type: ...
```

**`PydanticBuilder`** (defined in `_models.py`, exported):
- Implements `DTOBuilder.build()` using `json-schema-to-pydantic`
- Applies Patch 1: if `schema.get("additionalProperties") is False` → set
  `extra="forbid"` post-construction. Implementing agent must verify exact Pydantic v2
  post-construction API before writing code.
  Candidate: `model.model_config = ConfigDict(extra="forbid"); model.model_rebuild(force=True)`
  Evidence signal required: test must show actual `ValidationError` on extra field injection,
  not config attribute inspection.

**`build_model()` function** (internal, used by `PydanticBuilder`): unchanged shape.

`PydanticBuilder` is the default; exported from `weirding.__init__` so callers can import
it explicitly or subclass it.

Tests: `tests/test_models.py`
- `PydanticBuilder` produces a `BaseModel` subclass
- `additionalProperties: false` → actual `ValidationError` on extra field
- `$defs`/`$ref` round-trip
- A custom `DTOBuilder` implementation satisfies `isinstance(builder, DTOBuilder)` at runtime

Completion signal: `pytest tests/test_models.py -v` pass
Estimate: S–M (half to full day)

---

### Step 1c — Serializer + XML-to-dict
File: `src/weirding/_serializers.py` (new file)

Implements `to_xml()` and `_xml_to_dict()`. ADR-0005 must be Accepted before this step.

`to_xml(instance: BaseModel) -> str`:
- Root element = model class `__name__`
- Scalar → `<field>value</field>`; nested model → recurse; list → repeated children
  using `x-weirding-item-tag` from model JSON schema metadata

`_xml_to_dict(element: lxml.etree._Element, model_type: type) -> dict`:
- Schema-aware list coalescing: use Pydantic field type annotations (or `DTOBuilder`-supplied
  metadata) to determine which fields expect lists — not naive same-tag coalescing
- `parse()` in `__init__.py` imports and calls this as `_serializers._xml_to_dict(el, model)`

Tests: `tests/test_serializers.py`
- Round-trip: `parse(to_xml(instance), type(instance)) == instance` for flat, nested,
  array, optional-null

Completion signal: `pytest tests/test_serializers.py -v` pass
Estimate: M (1 day)

---

### Step 1d — API wiring + integration
File: `src/weirding/__init__.py` (Tier 1 protected — flagged for approval)

**Updated signatures:**
```python
def from_schema(
    schema: dict,
    *,
    name: str = "Model",
    builder: DTOBuilder | None = None,
) -> type:
    """
    Default: PydanticBuilder() → type[BaseModel].
    Pass any DTOBuilder for TypedDict, dataclass, Spark StructType, etc.
    """
    ...

def define_model(
    xml: str | bytes,
    *,
    builder: DTOBuilder | None = None,
) -> type:
    ...
```

With overloads for static type safety of the Pydantic default path:
```python
@overload
def from_schema(schema: dict, *, name: str = ...) -> type[BaseModel]: ...
@overload
def from_schema(schema: dict, *, name: str = ..., builder: DTOBuilder) -> type: ...
```

Wire:
- `compile(xml)` → `compile_schema(xml)`
- `from_schema(schema, name, builder)` → `(builder or PydanticBuilder()).build(schema, name=name)`
- `define_model(xml, builder)` → `from_schema(compile(xml), name=schema["title"] sanitized, builder=builder)`
- `parse(xml, model)` → `_serializers._xml_to_dict(lxml.etree.fromstring(xml, make_parser()), model)`
  then `model.model_validate(dict)`
- `to_xml(instance)` → `_serializers.to_xml(instance)`

**`__all__` additions:** `DTOBuilder`, `PydanticBuilder`

Tests: `tests/test_integration.py`
- Full round-trip with default (Pydantic) builder
- `from_schema(..., builder=CustomDTOBuilder())` — custom builder is invoked
- `define_model()` equivalent to two-step path
- `Validatable` Protocol: custom class with `model_validate` satisfies `parse()`
- Error paths: `ParseError`, `SchemaError`, `UnsupportedDialectError`

Completion signal: `uv run pytest` all pass, `uv run ruff check .` clean
Estimate: S–M (half to full day)

---

## Revised Roadmap

| Phase | Description |
|-------|-------------|
| ✅ 00 | Foundation — project setup, CI, core types |
| 📋 01 | Core Pipeline — annotation compiler, JSON Schema IR, `DTOBuilder` Protocol, `PydanticBuilder`, `compile()` + `from_schema()` + `define_model()` + `parse()` + `to_xml()` |
| 📋 02 | Prompt Utilities — `prompt.to_template()`, `prompt.format_error()`, `RetryContext` |
| 📋 03 | XSD Support — `weirding[xsd]` extra, `xmlschema`-based IR bridge, dialect auto-detection |
| 📋 04 | Distribution — pyproject.toml finalization, CI/CD pipeline, PyPI release, documentation |

---

## ADRs to update before Step 1b begins

- **ADR-0002 amendment**: `from_schema()` return type is `type` (not `type[BaseModel]`) when
  a custom `DTOBuilder` is provided. Default overload still returns `type[BaseModel]`.
  The JSON Schema IR contract is unchanged.
- **ADR-0004 amendment**: `PydanticBuilder` is the named default implementation of `DTOBuilder`.
  `build_model()` is its internal engine. The builder abstraction does not change the
  `json-schema-to-pydantic` engine choice or the two patches.
