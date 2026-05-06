# 0001: Schema Annotation Convention — Plain Unnamespaced Attributes

**Status:** Accepted

**Date:** 2026-05-06

**Authors:** Ben Lin

## Context

weirding requires a schema format that AI engineers use to define the XML structure they
want an LLM to produce. The schema serves two roles simultaneously: it is the compiler
input that produces a JSON Schema IR dict, and it is the source of the prompt template
shown to the LLM. These two roles create a tight constraint: the schema format must be
both machine-readable and LLM-legible.

Four annotation strategies were evaluated:

**`data-*` attributes** (`<field data-type="string" data-required="true"/>`)
The Lithium prototype used this convention. `data-*` is an HTML5 attribute convention
that is meaningful in browser/DOM contexts and reads oddly in enterprise XML documents.
It signals "HTML metadata" to any XML engineer encountering the file, which is the wrong
frame. Non-HTML XML validators will pass the attributes but the semantics are alien.
Rejected: wrong register for enterprise XML; no technical advantage over plain attributes.

**Namespace-prefixed attributes** (`<field r:type="string" r:required="true"/>`)
Namespace prefixes are the "standard" XML annotation mechanism for adding metadata from
an external vocabulary. Two blocking findings rule this out. First, Anthropic's ANTML
(their internal XML tool-calling format) uses namespace prefixes internally but strips
them at the API boundary in both directions — confirming that Claude cannot reliably
round-trip namespace prefixes. A schema using `r:type` will generate a prompt template
with `r:type`, which the model cannot faithfully reproduce. Second, Office Open XML
(a primary enterprise document target) exhausts every common single-letter namespace
prefix (`w:`, `r:`, `a:`, `p:`, `b:`, `c:`, `d:`, `f:`, `m:`, `o:`, `s:`, `t:`, `v:`,
`x:`). Any prefix weirding chose would collide with OOXML in mixed-document scenarios.
Rejected: LLM round-trip failure; namespace collision in enterprise XML.

**XSD as primary schema format**
XSD can express object, array, optional, and scalar types using `xs:complexType`,
`xs:sequence`, `xs:element`, `minOccurs`, `maxOccurs`. Research (dispatched May 2026)
found three blocking issues. First, no maintained Python runtime library converts XSD to
JSON Schema dict — weirding would own 100% of a multi-week semantic analysis engine
covering type derivation, substitution groups, cross-file imports, and nillable handling.
Second, the LLM prompt template workflow breaks: an XSD document for a 4-field object is
20+ lines of `xs:complexType/xs:sequence` markup, is context-budget waste, and inverts
the instance/schema relationship — LLMs are not trained to produce XML guided by XSD
grammar. Third, three weirding invariants (null types, `additionalProperties: false`,
`prefixItems` ban) have no clean XSD representation — workarounds require custom XSD
extensions, which is exactly a custom DSL with more moving parts.
XSD remains the correct Phase 03 extra for enterprise schema *import*; it is not the
right primary authoring format for LLM engineering workflows.

**Plain unnamespaced attributes** (`<field type="string" required="false"/>`)
Anthropic's own XML prompt engineering documentation uses this pattern: `index="n"`,
`weight="high"`, `source="filename"` — plain unnamespaced attributes with no prefix or
HTML convention. The attributes survive ANTML stripping. The schema document itself is
the LLM prompt template at near-zero transformation cost. The compiler is attribute
dispatch — O(number of supported attributes) — with no semantic analysis.

## Decision

weirding's native annotation dialect uses **plain unnamespaced attributes** on XML
elements to convey JSON Schema semantics. The element tag is the field name; the
attributes carry type and constraint metadata.

### Canonical attribute vocabulary

| Attribute | JSON Schema mapping | Notes |
|-----------|---------------------|-------|
| `type` | `type` | Values: `string`, `number`, `integer`, `boolean`, `object`, `array`, `null`. Default: inferred from children (object if children present, string otherwise). |
| `required` | entry in parent `required` array | Boolean string `"true"` / `"false"`. Default: `"true"`. |
| `description` | `description` | Human-readable; included verbatim in IR and prompt template. |
| `enum` | `enum` | Pipe-separated values: `"red\|green\|blue"`. |
| `pattern` | `pattern` | ECMAScript-compatible regex string. |
| `minimum` | `minimum` | Numeric lower bound (inclusive). For integers and numbers. |
| `maximum` | `maximum` | Numeric upper bound (inclusive). |
| `min` | `minLength` / `minItems` | For `type="string"`: `minLength`. For `type="array"`: `minItems`. |
| `max` | `maxLength` / `maxItems` | For `type="string"`: `maxLength`. For `type="array"`: `maxItems`. |
| `default` | `default` | Literal default value; type must be consistent with `type` attribute. |
| `nullable` | `type` promoted to `["T", "null"]` | Boolean string. Applies alongside the `type` attribute. |

### Array representation

Arrays use `type="array"` on the parent element with a single child element as the item
template. The child element defines the schema for each item.

```xml
<tags type="array">
  <tag type="string"/>
</tags>
```

Compiles to:
```json
{"tags": {"type": "array", "items": {"type": "string"}}}
```

Arrays of objects: the child element has its own children.

```xml
<results type="array">
  <result>
    <title type="string"/>
    <score type="number" required="false"/>
  </result>
</results>
```

### Object inference

An element with child elements and no explicit `type` attribute is inferred as
`type="object"`. This is the default for structured fields. `type="object"` may be
stated explicitly for clarity.

### Root element

The root element tag becomes the Pydantic model class name (sanitized to a valid Python
identifier). It is not a field — its children are the top-level fields.

### Avoided attribute names

`id`, `ref`, `name`, `base`, `use`, `form`, `nillable`, `abstract`, `block`,
`substitutionGroup` are XSD-reserved or conventionally meaningful in XML schema contexts.
Do not add these to the weirding vocabulary without an ADR.

### Scope

This convention applies to the **weirding native annotation dialect** only. XSD documents
are a separate dialect (Phase 03, `weirding[xsd]` extra) and are parsed by a different
compiler path. A weirding native annotation document and an XSD document are mutually
exclusive inputs to `compile()`.

## Consequences

### Positive

- Schema documents are directly usable as LLM prompt templates with no transformation.
  `prompt.to_template()` renders the element tree with type annotations as XML text,
  which is the exact format shown to the LLM.
- Compiler is simple: attribute dispatch with no semantic analysis graph. Test surface
  is linear in the attribute vocabulary.
- No namespace machinery. Documents load cleanly in any XML editor or validator.
- Anthropic XML prompt engineering best practices confirm this pattern: Claude produces
  higher-quality structured output when guided by readable example XML, not grammar
  documents.
- OOXML and SOAP documents (enterprise targets) can coexist in the same project without
  prefix collision.

### Negative

- Not a recognized standard. Enterprise XML tooling (oXygen, VS Code XML extension) will
  validate the documents as well-formed XML but will not provide attribute-level
  completion or semantic validation for weirding-specific attributes.
- `type` and `required` are common English words. If a user's actual data model has a
  field genuinely named `type` or `required`, the attribute convention creates an
  ambiguity that must be resolved by escaping or renaming. (Mitigation: document this
  explicitly and provide guidance on renaming data fields.)

### Neutral

- `data-*` attributes from the Lithium prototype (`xml-pydantic`) are **not** ported.
  Any port of prototype logic must replace `data-type`, `data-required`, etc. with the
  plain attribute equivalents defined here.
- Future additions to the attribute vocabulary require an ADR update or a new ADR. The
  vocabulary is intentionally narrow to keep the compiler surface auditable.
- XSD schema documents fed to `compile()` are detected by the presence of the
  `{http://www.w3.org/2001/XMLSchema}schema` root element and routed to the XSD compiler
  path (Phase 03). This detection logic is the correct scope for the XSD-native path.
