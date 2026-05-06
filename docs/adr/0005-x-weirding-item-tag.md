# 0005: x-weirding-item-tag Extension Key in JSON Schema IR

**Status:** Accepted

**Date:** 2026-05-06

**Authors:** Ben Lin

## Context

weirding's `to_xml()` serializer must reconstruct the correct XML element tag name when
serializing list fields. Given a schema like:

```xml
<response>
  <tags type="array">
    <tag type="string"/>
  </tags>
</response>
```

The compiled model has a field named `tags` whose items should serialize as `<tag>` child
elements. Without this information, `to_xml()` cannot produce output that round-trips
cleanly through `parse()`.

This information must flow from the schema compiler (`_schema.py`) to the serializer
(`_serializers.py`). Three paths for carrying it were evaluated:

**Option A — Store in JSON Schema IR as `x-weirding-item-tag`**
JSON Schema permits unrecognized extension keywords. By convention, `x-*` prefixed keys
are extension properties; standard validators and consumers tolerate and ignore them.
The compiled IR dict for an array field would be:
```json
{
  "type": "array",
  "items": {"type": "string"},
  "x-weirding-item-tag": "tag"
}
```
`compile()` returns a self-contained dict. Every consumer — Databricks, `jsonschema`,
`from_schema()` — receives the item tag alongside the schema without a second call.

**Option B — Strip from `compile()` output; store in model class attribute**
`compile()` would return a clean JSON Schema dict with no extension keys. The item tag
would be stored in a separate metadata dict passed alongside the schema, or set as a
class attribute (`__weirding_meta__`) on the generated model. The serializer would read
it from the model at `to_xml()` time.

This splits the self-contained IR into two artifacts that must be kept in sync. A caller
who caches the schema dict but not the metadata dict loses the item tag. The `compile()`
output no longer describes the full round-trip contract. For Databricks users who pass the
dict to `from_schema()` via a separate code path, metadata loss is a silent bug.

**Option C — Derive item tag at `to_xml()` time via singularization**
`to_xml()` would singularize the field name at runtime: `tags` → `tag`, `results` →
`result`, etc. This avoids extending the IR entirely. However, English singularization is
a heuristic that fails on irregular plurals (`children`, `people`, `data`, `criteria`,
`indices`), domain-specific nouns (`status`, `news`, `species`), and non-English names
common in enterprise XML. Silent divergence from the schema's declared child tag name is
a round-trip integrity failure. This option was rejected as insufficiently reliable for a
library targeting production enterprise XML.

## Decision

weirding's JSON Schema IR includes `x-weirding-item-tag` as an extension key on every
array-type field that has a named child element in the schema. The key is part of the
public IR contract (alongside the restrictions documented in ADR-0002).

The key is set by `compile_schema()` in `_schema.py` and consumed by `to_xml()` in
`_serializers.py`. `from_schema()` stores it in model metadata (e.g., in a `__weirding_meta__`
class attribute or via `model.model_fields` annotation) so that `to_xml()` can retrieve
it from the model class without requiring the original schema dict at serialization time.

Standard JSON Schema consumers (`jsonschema.validate()`, OpenAPI tools, Databricks schema
converters) follow the JSON Schema specification: unrecognized keys are ignored. The
extension key does not affect validation behavior in any standard consumer.

If an array field in the annotation schema has no child element (e.g., `<tags type="array"/>`
with no child), `x-weirding-item-tag` is omitted and `to_xml()` falls back to `"item"` as
the default child tag name.

## Consequences

### Positive

- `compile()` output is self-contained — a single dict carries all information needed to
  both build a model and round-trip serialize it.
- `to_xml()` always produces XML that `parse()` can re-parse without configuration.
- No heuristic failures: the item tag is always the exact tag name from the schema.
- Extension key pattern is widely understood; no consumer will be confused by an `x-*`
  key it does not recognize.

### Negative

- `compile()` output is not pure JSON Schema draft 2020-12 — it contains a weirding
  extension key. This must be clearly documented in the `compile()` docstring.
- Downstream tools that copy-paste the IR into an OpenAPI spec or JSON Schema registry
  will carry the extension key unless they strip it. The key is harmless but may require
  a strip step in some pipelines.

### Neutral

- The default fallback (`"item"`) for schemas without a named child element must be
  documented. Callers who use `<list type="array"/>` without a child element will get
  `<item>` tags in serialized output.
- Future XSD dialect compiler (Phase 03) must also emit `x-weirding-item-tag` for array
  types derived from `maxOccurs="unbounded"` elements, inferring the tag name from the
  repeated element name.
