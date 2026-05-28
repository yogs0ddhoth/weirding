# Plan: Phase 02 — Prompt Utilities

**Planner verdict:** PROCEED WITH MODIFICATIONS (incorporated below)  
**Branch to create before implementation:** `feat/phase-02-prompt-utilities`  
**Base:** `main` (current HEAD `fb1de35`)  
**Planned by:** Claude Sonnet 4.6 on 2026-05-06

---

## Protected Files Check

| File | Tier | Action |
|------|------|--------|
| `src/weirding/_parser.py` | Tier 1 | NOT TOUCHED |
| `src/weirding/__init__.py` | Tier 1 | NOT TOUCHED — prompt utilities remain in `weirding.prompt` submodule |
| `src/weirding/_schema.py` | Tier 2 | NOT TOUCHED |
| `src/weirding/_models.py` | Tier 2 | NOT TOUCHED |
| `src/weirding/_serializers.py` | Tier 2 | MODIFIED — refactor `_item_tag_for_field()` signature only (see Phase A) |
| `src/weirding/prompt.py` | None | PRIMARY TARGET — stubs replaced with implementations |
| `src/weirding/_exceptions.py` | None | NOT TOUCHED (no new exception types needed) |

**Tier 2 justification for `_serializers.py`:** `_item_tag_for_field(model: BaseModel, field_name: str)` takes a model *instance*, but `to_template()` operates on `type[BaseModel]`. Duplicating the three-priority resolution logic into `prompt.py` creates two implementations that can silently diverge when ADR-0005 fallback behavior changes. The correct fix is to refactor the signature to `_item_tag_for_field(field_name: str, field_info: FieldInfo) -> str` and update the single existing call site in `_populate_element()`. This is purely internal plumbing — the function is not part of the public API and the change is not observable by callers.

---

## Simplicity Challenge

**Simplest approach considered:** One phase implementing all three APIs together.

**Why two phases:** `to_template()` is independent of `format_error()` and `RetryContext`
and can be verified complete before the error-handling code is written. Two phases is the
minimum meaningful breakdown — grouping `format_error()` and `RetryContext` in Phase B is
correct because they share the same error formatting path.

---

## Phase A — `to_template()` + serializer refactor

**Estimate:** 2–3 hours

### Files

| File | Action |
|------|--------|
| `src/weirding/_serializers.py` | Refactor `_item_tag_for_field()` signature to `(field_name: str, field_info: FieldInfo) -> str`; update `_populate_element()` call site |
| `src/weirding/prompt.py` | Replace `to_template()` stub with full implementation |
| `tests/test_prompt.py` | Create; write `to_template` test suite |

### Serializer Refactor Specification

Change `_item_tag_for_field(model: BaseModel, field_name: str) -> str` to
`_item_tag_for_field(field_name: str, field_info: FieldInfo) -> str`.

Old call site in `_populate_element()`:
```python
item_tag = _item_tag_for_field(instance, field_name)
```

New call site:
```python
field_info = model_cls.model_fields[field_name]
item_tag = _item_tag_for_field(field_name, field_info)
```

The three-priority logic inside the function is unchanged:
1. `field_info.json_schema_extra.get("x-weirding-item-tag")` if present
2. Strip trailing "s" if field name ends with "s" and has length > 1
3. Literal `"item"`

All existing tests in `tests/test_serializers.py` must still pass after this refactor —
the behavior is identical, only the parameter form changes.

### `to_template()` Implementation Specification

Source of truth: `model.model_fields` (not `model.model_json_schema()`). The Pydantic
model carries all needed metadata directly; no JSON Schema roundtrip required.

**Field type dispatch (evaluated in this order):**

1. **Optional / nullable** — check both union forms (Python 3.11+ is confirmed per MEMORY.md):
   ```python
   import types as _types
   def _is_optional(ann) -> bool:
       return (
           isinstance(ann, _types.UnionType)          # X | None (3.10+ runtime syntax)
           or (get_origin(ann) is Union                # typing.Optional[X]
               and type(None) in get_args(ann))
       )
   def _unwrap_optional(ann):
       return next(a for a in get_args(ann) if a is not type(None))
   ```
   Unwrap the inner type, mark the field with `<!-- optional -->` comment before its element.

2. **List** — `get_origin(annotation) is list`; render two repeated child elements using
   `_item_tag_for_field(field_name, field_info)` (the refactored helper), followed by
   `<!-- repeat as needed -->` comment.

3. **Nested object** — `isinstance(annotation, type) and issubclass(annotation, BaseModel)`;
   recurse into the nested model for child elements.

4. **Enum (Literal)** — `get_origin(annotation) is Literal` (after unwrapping Optional);
   render as scalar placeholder with `<!-- allowed values: a | b | c -->` comment.
   Values from `get_args(annotation)`.

5. **Boolean scalar** — `annotation is bool`; element text is `"true"` (NOT `"boolean"`).
   Research-confirmed: "boolean" causes True/False/yes/no drift in LLM output.

6. **Other scalars** — `str→"string"`, `int→"integer"`, `float→"number"`. Unknown: `"string"`.

**Comment placement:** `lxml.etree.Comment(" text ")` inserted into parent *before* the
field element. `etree.tostring(root, encoding="unicode", pretty_print=True)`.

**Annotation ordering:** description first, `<!-- optional -->` second (when both apply).

**Root element tag:** `model.__name__` (same source as `to_xml()`).

**NOT included:** No XML declaration, no namespace declarations, no `type=`/`required=`/`enum=`
attributes on template elements (schema/instance confusion per ADR-0001).

**Concrete expected output** (model: id:str, customer_name:str+description,
status:Literal["pending","confirmed","shipped"], notes:Optional[str], items:list[object]):

```xml
<Order>
  <id>string</id>
  <!-- The customer's full name. -->
  <customer_name>string</customer_name>
  <!-- allowed values: pending | confirmed | shipped -->
  <status>string</status>
  <!-- optional -->
  <notes>string</notes>
  <items>
    <item>
      <product_id>string</product_id>
      <quantity>integer</quantity>
    </item>
    <item>
      <product_id>string</product_id>
      <quantity>integer</quantity>
    </item>
    <!-- repeat as needed -->
  </items>
</Order>
```

### Test Coverage (Phase A)

- Scalar fields: str, int, float, bool (verify `"true"` not `"boolean"`)
- Field with `description` — comment appears before element
- Optional field — `<!-- optional -->` comment present
- Optional field with description — both comments, description first
- Enum (Literal) field — `<!-- allowed values: ... -->` with all values
- Nested object field — child elements recurse correctly
- List of scalars — two child elements + `<!-- repeat as needed -->`
- List of objects — two child elements each with correct sub-structure
- Optional list field — `<!-- optional -->` before wrapper element
- Root tag equals `model.__name__`
- Output is well-formed XML (parse with `make_parser()` — no exceptions raised)
- Note: use `etree.fromstring()` for structural assertions rather than raw string equality
  (lxml `pretty_print=True` may emit a trailing newline; exact-string comparisons are fragile)

### Completion Signal

```
uv run pytest tests/test_prompt.py -k "to_template" -v   # all pass
uv run pytest tests/test_serializers.py -v                # still all pass (regression check)
uv run ruff check .                                        # clean
```

---

## Phase B — `format_error()` + `RetryContext`

**Estimate:** 1–2 hours

### Files

| File | Action |
|------|--------|
| `src/weirding/prompt.py` | Replace `format_error()` stub; implement `RetryContext` |
| `tests/test_prompt.py` | Add `format_error` and `RetryContext` test suite |

### `format_error()` Implementation Specification

```python
from pydantic import ValidationError

def format_error(error: Exception, *, model: type[BaseModel]) -> str:
    # Unwrap ParseError — weirding raises ParseError(str(exc)) from exc
    if isinstance(error, ParseError) and isinstance(error.__cause__, ValidationError):
        ve = error.__cause__
    elif isinstance(error, ValidationError):
        ve = error
    else:
        return f"Unexpected error: {error}"

    lines = []
    for err in ve.errors(include_url=False, include_input=False, include_context=True):
        # PRIVACY: include_input=False is MANDATORY. LLM output may contain user PII.
        # Never change this default. Any future include_values=True opt-in requires
        # an explicit privacy review comment in the code.
        path = _loc_to_path(err["loc"])
        msg = err["msg"]
        lines.append(f"  - {path}: {msg}" if path else f"  - {msg}")

    count = ve.error_count()
    noun = "error" if count == 1 else "errors"
    return f"The previous response had {count} validation {noun}:\n" + "\n".join(lines)


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    """Convert Pydantic v2 loc tuple to dot-bracket notation.

    ("items", 0, "name") → "items[0].name"
    ("status",) → "status"
    () → ""
    ("__root__",) → ""   # filter Pydantic root-validator loc component
    """
    parts: list[str] = []
    for part in loc:
        if part == "__root__":
            continue   # root-validator artifact; not useful in retry message
        if isinstance(part, int):
            if parts:
                parts[-1] = parts[-1] + f"[{part}]"
            else:
                parts.append(f"[{part}]")
        else:
            parts.append(str(part))
    return ".".join(parts)
```

`model` parameter accepted but unused (reserved for future field-description enrichment).

### `RetryContext` Implementation Specification

```python
class RetryContext:
    def __init__(self, model: type[BaseModel], max_attempts: int = 3) -> None:
        self._model = model
        self._max_attempts = max_attempts
        self._attempt = 0
        self._last_message: str | None = None

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def exceeded(self) -> bool:
        return self._attempt >= self._max_attempts

    def record_error(self, error: Exception) -> None:
        self._attempt += 1
        self._last_message = format_error(error, model=self._model)

    def retry_message(self) -> str:
        return self._last_message or ""
```

Note: the existing stub declares `__init__(self, model)` without `max_attempts`. The plan
adds `max_attempts: int = 3`. This is additive, not a breaking change, and `prompt.py`
is not a protected file — the implementer must update the stub signature.

### Test Coverage (Phase B)

**`format_error()`:**
- Missing required field → field name in path, "Field required" in message
- Wrong type (int field, receives string) → correct path and type message
- Extra field with `extra="forbid"` → "Extra inputs are not permitted"
- Constraint violation (`greater_than`) → message includes constraint value
- `ParseError` wrapping `ValidationError` → unwrapped correctly
- `ParseError` without `ValidationError` cause → fallback message returned
- Non-ValidationError exception → fallback message returned
- Multiple errors → all in output; header count correct
- Nested field path → dot notation (`parent.child`)
- List item path → bracket notation (`items[0].name`)
- Privacy guard: output string contains no raw XML from the failed parse (regression barrier)

**`RetryContext`:**
- Initial: `attempt == 0`, `exceeded == False`
- After one `record_error()`: `attempt == 1`, `retry_message()` non-empty
- After `max_attempts` calls: `exceeded == True`
- `retry_message()` before any `record_error()` → `""` (no crash)
- End-to-end: define model → parse bad XML → `record_error()` → `retry_message()` contains the failed field name

### Completion Signal

```
uv run pytest tests/test_prompt.py -v   # full suite (A + B) all pass
uv run ruff check .                      # clean
```

---

## ADR Candidates

None. Rendering format follows ADR-0001. Privacy constraints covered by ETHOS.md and CLAUDE.md.
`RetryContext` has no credible design alternatives crossing component boundaries.

---

## Post-Completion Checklist

- [ ] `uv run pytest` — all tests pass (≥85 expected, up from 66)
- [ ] `uv run ruff check .` — zero warnings
- [ ] `uv run ruff format .` — no diffs
- [ ] Update `.claude/memory/MEMORY.md` — mark Phase 02 complete, advance to Phase 03
- [ ] Update `docs/planning/PROJECT_ROADMAP.md` — Phase 02 status to ✅
- [ ] Conventional commit: `feat(prompt): implement to_template, format_error, and RetryContext`
- [ ] Co-authorship trailers for Ben Lin and Claude Sonnet 4.6
- [ ] PR against `main`
