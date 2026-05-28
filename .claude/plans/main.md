# Plan: Phase 03 — XSD Support

**Branch to create before implementation:** `feat/phase-03-xsd-support`
**Base:** `main` (current HEAD `3ae1c79`)
**Planned by:** Claude Sonnet 4.6 on 2026-05-28

---

## Context

Phase 02 complete (105 tests). XSD support is pre-gated in `_schema.py`: when the root element
tag is `{http://www.w3.org/2001/XMLSchema}schema`, it raises
`UnsupportedDialectError("XSD support requires weirding[xsd]")`. The `[xsd]` extra is declared
in `pyproject.toml` with an empty dependency list. Phase 03 fills in the bridge.

No new public API is required: `compile()` already accepts XSD strings and auto-detects the
dialect. The bridge wires into the existing detection point in `_schema.py`.

---

## Protected Files

| File | Tier | Action |
|------|------|--------|
| `src/weirding/_parser.py` | Tier 1 | **NOT TOUCHED** |
| `src/weirding/__init__.py` | Tier 1 | **NOT TOUCHED** — `compile()` public signature is unchanged |
| `src/weirding/_schema.py` | Tier 2 | MODIFIED — replace 1-line `raise` with 5-line conditional bridge dispatch |
| `src/weirding/_models.py` | Tier 2 | **NOT TOUCHED** |

**Tier 2 justification for `_schema.py`:** The existing `UnsupportedDialectError` guard must
be replaced with a conditional import that calls the bridge when `xmlschema` is installed and
falls back to the same error when it is not. This is the minimal surgical change: one `if`-block
replaces one `raise` statement. All other logic in `compile_schema()` is unchanged.

---

## Simplicity Challenge

**Simplest approach considered:** Inline the XSD → IR logic directly inside `_schema.py`'s
`compile_schema()` function. No sub-package, no separate module.

**Why the plan adds a sub-package instead:** `_schema.py` is Tier 2 protected; the review
requirement is to minimize the diff. MEMORY.md pre-decides `src/weirding/xsd/` as the bridge
location. XSD traversal is substantial enough to need independent testability. Isolating it in
`src/weirding/xsd/_bridge.py` keeps the hot paths (native annotation vs XSD) independently
testable without touching each other, and the diff to `_schema.py` is as small as possible.

---

## ADR Candidates

1. **XSD library choice (ADR-0006):** `xmlschema` vs alternatives. No maintained Python runtime
   XSD converter exists except `xmlschema`. Document the choice, dependency scope (optional
   extra only, never base), and version floor rationale.
2. **String-based XSD parsing (ADR-0006 or addendum):** How to pass in-memory XSD string to
   `xmlschema.XMLSchema` without network/filesystem side effects. Using `io.StringIO` with
   `defuse="all"` is the approach; needs a record because it has security and portability
   implications for schemas using `xs:import`.

---

## Phase 03a — Foundation (pyproject + wiring + package scaffold)

**Estimate:** 1–1.5h

### Files created

| File | Content |
|------|---------|
| `src/weirding/xsd/__init__.py` | Package marker; re-exports `xsd_to_ir` |
| `src/weirding/xsd/_bridge.py` | `xsd_to_ir(xml: str \| bytes) -> dict` — full implementation (see spec below) |

### Files modified

| File | Change |
|------|--------|
| `pyproject.toml` | Add `xmlschema>=3.0` to `[xsd]` extra; add `"weirding[xsd]"` to `dev` extra |
| `CLAUDE.md` | Update Build command to `uv sync --extra dev` (dev already pulls xsd transitively) |
| `src/weirding/_schema.py` (Tier 2) | Replace `raise UnsupportedDialectError(...)` with conditional bridge dispatch |

### `_schema.py` change (exact diff)

Replace:
```python
if root.tag == _XSD_SCHEMA_TAG:
    raise UnsupportedDialectError("XSD support requires weirding[xsd]")
```

With:
```python
if root.tag == _XSD_SCHEMA_TAG:
    try:
        from weirding.xsd._bridge import xsd_to_ir
    except ImportError as exc:
        raise UnsupportedDialectError("XSD support requires weirding[xsd]") from exc
    return xsd_to_ir(root)
```

Note: pass the already-parsed `root` element (not the raw XML string) to avoid re-parsing.
`xsd_to_ir` must accept either a raw XML string/bytes *or* an `lxml.etree._Element`.

### `_bridge.py` specification

```python
def xsd_to_ir(source: str | bytes | etree._Element) -> dict:
    """Convert an XSD document to a JSON Schema IR dict.

    Accepts a raw XSD string/bytes or an already-parsed lxml Element (root
    <xs:schema> element). When a string/bytes is passed it is parsed via
    weirding._parser.make_parser() before being handed to xmlschema.
    """
```

**Entry points:**

`xsd_to_ir` has a single public signature: `xsd_to_ir(source: etree._Element) -> dict`.
It accepts only an already-parsed lxml element (as passed from `_schema.py`).

A private `_xsd_to_ir_from_bytes(xml_bytes: bytes) -> dict` helper exists for standalone
test use only. It is NOT called from `_schema.py` and is NOT exported from `__init__.py`.

**`xmlschema` instantiation (security posture):**
```python
import xmlschema

def _build_xs_schema(root: etree._Element) -> xmlschema.XMLSchema:
    return xmlschema.XMLSchema(root, defuse="always")
```

`defuse="always"` prevents entity expansion. Do NOT use `defuse="remote"` (default) — our
threat model prohibits network side-effects entirely. Defense-in-depth: lxml's
`make_parser()` already defuses the element before it reaches `xsd_to_ir`, so `defuse="always"`
is a second layer.

**Root element selection:** Use the first element declaration in `xs_schema.elements`. If
`xs_schema.elements` is empty, raise `SchemaError("XSD has no top-level element declarations")`.

**Title:** local name of the root element declaration.

**Type mapping table (`_XSD_TYPE_MAP`):**

Keys are Clark-notation URIs (`t.name`), not prefixed names (`t.prefixed_name`). The prefix (`xs:`) is schema-local and not reliable. Lookup via `_XSD_TYPE_MAP.get(type_obj.name, {"type": "string"})`.

| Clark-form key | JSON Schema |
|----------------|-------------|
| `{http://www.w3.org/2001/XMLSchema}string`, `normalizedString`, `token`, `anyURI`, `ID`, `IDREF`, `Name`, `NCName`, `NMTOKEN` | `{"type": "string"}` |
| `{http://www.w3.org/2001/XMLSchema}integer`, `int`, `long`, `short`, `byte`, `nonNegativeInteger`, `positiveInteger`, `unsignedInt`, `unsignedLong`, `unsignedShort`, `unsignedByte` | `{"type": "integer"}` |
| `{http://www.w3.org/2001/XMLSchema}decimal`, `float`, `double` | `{"type": "number"}` |
| `{http://www.w3.org/2001/XMLSchema}boolean` | `{"type": "boolean"}` |
| `{http://www.w3.org/2001/XMLSchema}date` | `{"type": "string", "format": "date"}` |
| `{http://www.w3.org/2001/XMLSchema}time` | `{"type": "string", "format": "time"}` |
| `{http://www.w3.org/2001/XMLSchema}dateTime` | `{"type": "string", "format": "date-time"}` |
| All others (duration, gYear, gMonth, gDay, hexBinary, base64Binary, etc.) | `{"type": "string"}` |

(In code: keys can be generated as `f"{{http://www.w3.org/2001/XMLSchema}}{local}"` for each local name.)

**Completion signal:**
```
uv run pytest tests/test_xsd.py -k "flat or title or missing_extra" -v   # pass
uv run ruff check .                                                         # clean
```

---

## Phase 03b — Complex types + optional fields + nillable

**Estimate:** 2–3h

### Files modified

| File | Change |
|------|--------|
| `src/weirding/xsd/_bridge.py` | Implement `_complex_type_to_ir()`, optional element handling, nullable (`nillable`) |

### Specification

**`simpleContent` guard (required — blocking correctness):**

Before iterating a complex type's content, guard against `xs:simpleContent`:
```python
from xmlschema.validators import XsdGroup

def _iter_elements(complex_type):
    content = getattr(complex_type, "content", None)
    if not isinstance(content, XsdGroup):
        return  # xs:simpleContent — scalar type, not iterable
    yield from content
```

When `content` is not an `XsdGroup` (e.g. `xs:simpleContent` extending a scalar type),
the element's type is treated as a scalar — fall back to `_xsd_type_to_ir(elem_decl.type)`
rather than iterating. Without this guard, `xs:simpleContent` raises `TypeError`.

**Complex type traversal (after guard):**

```
for elem_decl in _iter_elements(complex_type):
    field_name = elem_decl.local_name
    min_occurs = elem_decl.min_occurs  # 0 → optional
    max_occurs = elem_decl.max_occurs  # None → unbounded
    nillable   = elem_decl.nillable    # bool
    field_ir   = _elem_decl_to_ir(elem_decl)
    properties[field_name] = field_ir
    if min_occurs != 0:
        required.append(field_name)
```

For `xs:choice`, emit a `oneOf` with each branch as a separate object schema
(see Known Limitations below for partial support).

**Nillable (`nillable="true"`):** wrap the element's IR in an anyOf null-union, matching
the same `_wrap_nullable()` pattern from `_schema.py`:
```python
if nillable:
    ir = {"anyOf": [ir, {"type": "null"}]}
```

**`xs:annotation` / `xs:documentation`:** if present on an element declaration, populate
`"description"` in the field's IR dict.

**`additionalProperties` / `extra="forbid"` behavior:**

XSD has no `additionalProperties` concept. The XSD bridge never emits
`"additionalProperties": false` in its IR. Therefore the `build_model()` `extra="forbid"`
patch (MEMORY.md rule 12) will NOT fire for XSD-derived models. This is correct and
intentional — XSD-derived Pydantic models use the default `extra="ignore"` behavior.

**Completion signal:**
```
uv run pytest tests/test_xsd.py -k "not array and not enum" -v   # pass
uv run ruff check .                                                 # clean
```

---

## Phase 03c — Array fields + enumerations + integration

**Estimate:** 1.5–2h

### Files modified

| File | Change |
|------|--------|
| `src/weirding/xsd/_bridge.py` | Add array handling (`maxOccurs > 1`), enum handling (`xs:restriction` + `xs:enumeration`) |
| `tests/test_xsd.py` | Add array tests, enum tests, end-to-end integration tests |

### Array field specification

When `max_occurs is None` (unbounded) or `max_occurs > 1`:

```python
item_ir = _elem_decl_to_ir(elem_decl, as_item=True)  # strip array wrapper recursion guard
field_ir = {
    "type": "array",
    "items": item_ir,
    "x-weirding-item-tag": elem_decl.local_name,
}
if elem_decl.min_occurs is not None and elem_decl.min_occurs > 0:
    field_ir["minItems"] = elem_decl.min_occurs
if elem_decl.max_occurs is not None:
    field_ir["maxItems"] = elem_decl.max_occurs
```

The wrapper element's local name becomes both the field name in the parent object AND
`x-weirding-item-tag` (same element is repeated, consistent with native-annotation convention).

### Enum field specification

A simple type with `xs:restriction` + `xs:enumeration` facets maps to JSON Schema `enum`:

```python
if hasattr(type_obj, "enumeration") and type_obj.enumeration:
    base_ir = _xsd_type_to_ir(type_obj.base_type)  # get the base type dict
    return {**base_ir, "enum": list(type_obj.enumeration)}
```

Values are taken directly (strings if base is string, ints if base is integer, etc.).

### Integration test specification

```python
@pytest.mark.parametrize("xsd_fixture,expected_title,field_checks", [...])
def test_compile_define_parse_round_trip(xsd_fixture, expected_title, field_checks):
    ir = compile(xsd_fixture)
    assert ir["title"] == expected_title
    Model = from_schema(ir, name=expected_title)
    instance = parse(sample_xml_for(xsd_fixture), Model)
    assert to_xml(instance)  # no exception; round-trip completes
```

Cover at minimum:
1. Flat XSD → compile → from_schema → parse → to_xml
2. Nested complex type XSD
3. Array field XSD

### Files modified (docs + memory)

| File | Change |
|------|--------|
| `docs/planning/PROJECT_ROADMAP.md` | Phase 03 → ✅ complete |
| `.claude/memory/MEMORY.md` | Advance current phase to 04; record `xmlschema>=3.0` as `[xsd]` dep; record `defuse="always"` posture |

**Completion signal:**
```
uv run pytest                    # all tests pass (105 + new XSD suite)
uv run ruff check .              # zero warnings
uv run ruff format . --check     # no diffs
```

---

## Known Limitations (document in module docstring, not blocking Phase 03)

- `xs:choice` model groups: partially supported (each alternative becomes a separate
  `oneOf` branch). Complex nested choices may not round-trip correctly via `parse()`.
- `xs:extension` / `xs:restriction` on complex content (inheritance): not supported.
  Elements using inheritance will produce incomplete property sets.
- `xs:import` / `xs:include`: `defuse="always"` blocks network resolution. Local
  `xs:include` via relative path will fail (by design — we receive XSD as an in-memory
  string, not a file path).
- Multiple top-level element declarations: only the first is used as the root. Future
  API enhancement (`compile(xsd, root="ElementName")`) deferred to Phase 04+.

---

## Total Estimate: 5–7h

---

## Post-Completion Checklist

- [ ] `uv run pytest` — all tests pass
- [ ] `uv run ruff check .` — zero warnings
- [ ] `uv run ruff format . --check` — no diffs
- [ ] Update `.claude/memory/MEMORY.md` — mark Phase 03 complete, advance to Phase 04
- [ ] Update `docs/planning/PROJECT_ROADMAP.md` — Phase 03 status to ✅
- [ ] ADR-0006 authored for XSD library choice and string-parsing posture
- [ ] Conventional commit: `feat(xsd): implement XSD → JSON Schema IR bridge (weirding[xsd])`
- [ ] Co-authorship trailers for Ben Lin and Claude Sonnet 4.6
- [ ] PR against `main`
