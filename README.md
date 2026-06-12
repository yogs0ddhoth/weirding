# weirding

**XML ↔ JSON Schema ↔ Pydantic v2 conversion for structured-output AI workflows.**

weirding lets you author a schema once as plain XML (or XSD) and convert it freely in
every direction: into an inspectable JSON Schema dict, into Pydantic v2 model classes, into
provider-ready schemas for OpenAI/Azure, Databricks, and open-weight runtimes — and all the
way back. The XML you write becomes a single source of truth for validation, structured LLM
output, and round-trip serialization.

```bash
pip install weirding
```

```python
import weirding

Model = weirding.define_model("""
<Response>
  <name type="string" required="true"/>
  <score type="integer" required="true"/>
</Response>
""")

instance = weirding.parse("<Response><name>Alice</name><score>42</score></Response>", Model)
# Response(name='Alice', score=42)
```

📚 **Full documentation:** <https://yogs0ddhoth.github.io/weirding/>

---

## The conversion triangle

weirding models three representations of the same schema and the edges between them:

```
            compile()                from_schema()
   XML  ───────────────▶  JSON Schema IR  ───────────────▶  Pydantic model
 schema  ◀───────────────     (dict)      ◀───────────────    (BaseModel)
            dump_xml()               to_schema()
```

- **XML schema** — what you author, using a plain-attribute annotation convention or XSD.
- **JSON Schema IR** — an inspectable `dict` (JSON Schema draft 2020-12 subset). This is the
  core product: consume it directly, validate against it, or export it for any provider.
- **Pydantic model** — a generated `BaseModel` subclass for validation and typed access.

Every edge has a function, so the loop is genuinely 3-way (see
[ADR-0012](docs/adr/0012-reverse-edge-fungibility.md)). `parse()` and `to_xml()` add the
data-level round trip on top of the schema-level triangle.

---

## API

| Function | Direction | Purpose |
|----------|-----------|---------|
| `compile(xml)` | XML schema → IR | Convert an XML/XSD schema document to a JSON Schema IR dict |
| `from_schema(ir, *, name, builder)` | IR → model | Build a Pydantic model (or custom DTO) from an IR dict |
| `define_model(xml)` | XML schema → model | `compile` + `from_schema` in one call; names the class from the root element |
| `parse(xml, model)` | XML data → instance | Validate and bind an XML data document into a typed instance |
| `to_xml(instance)` | instance → XML data | Serialize a model instance back to an XML string (round-trips with `parse`) |
| `to_schema(model)` | model → IR | Reverse edge: derive an IR dict back out of a Pydantic model |
| `dump_xml(ir)` | IR → XML schema | Reverse edge: re-emit a canonical XML schema document from an IR |
| `to_json_schema(ir, *, strict)` | IR → provider schema | Export a provider-ready JSON Schema (clean draft 2020-12, or strict OpenAI ∩ Databricks) |

Also exported: `JsonSchemaIR` (the IR type alias), the `DTOBuilder` / `Validatable`
protocols and default `PydanticBuilder`, and the exception hierarchy `WeirdingError` →
`SchemaError` / `ParseError` / `UnsupportedDialectError`.

### Installation

```bash
pip install weirding          # core
pip install "weirding[xsd]"   # + XSD schema support (xmlschema bridge)
```

Requires Python 3.11+. Core dependencies: `pydantic`, `lxml`, `json-schema-to-pydantic`.

---

## Authoring schemas

weirding's native dialect is a **plain-attribute annotation convention**: ordinary XML
elements, with JSON Schema constraints expressed as attributes.

```python
import weirding

schema_xml = """
<Response>
  <name type="string" required="true" description="Full name"/>
  <age type="integer" required="true" minimum="0"/>
  <bio type="string" required="false"/>
  <tags type="array">
    <tag type="string"/>
  </tags>
</Response>
"""

ir = weirding.compile(schema_xml)        # inspectable JSON Schema dict
Model = weirding.define_model(schema_xml) # Pydantic v2 BaseModel
```

`compile()` → `from_schema()` is stateless and idempotent — call it once at startup and
cache the generated class rather than rebuilding it per request.

### XSD support

With the `xsd` extra installed, weirding auto-detects an XSD document from its root-element
namespace, so the same functions accept XSD transparently:

```python
Model = weirding.define_model("""
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Person">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="name" type="xs:string"/>
        <xs:element name="age" type="xs:integer"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
""")
```

### Round trip and reverse edges

```python
import weirding

Model = weirding.define_model("<Point><x type='number'/><y type='number'/></Point>")

# data round trip: parse(to_xml(x)) == x
p = weirding.parse("<Point><x>1.0</x><y>2.0</y></Point>", Model)
weirding.to_xml(p)                     # "<Point><x>1.0</x><y>2.0</y></Point>"

# schema round trip via the reverse edges
ir = weirding.to_schema(Model)         # Pydantic model  → IR dict
xml_schema = weirding.dump_xml(ir)     # IR dict         → XML schema document

# model straight to XML schema is the one-liner:
weirding.dump_xml(weirding.to_schema(Model))
```

`dump_xml()` serializes a **schema** (the authoring document, inverse of `compile`);
`to_xml()` serializes a **data instance** (inverse of `parse`). They are not the same edge.

---

## Structured-output interop

The IR is the bridge to the rest of the ecosystem. `to_json_schema()` exports a
provider-ready schema:

```python
ir = weirding.compile(schema_xml)

# Permissive draft 2020-12 — vLLM, Ollama, jsonschema.validate
weirding.to_json_schema(ir)

# Strict OpenAI ∩ Databricks intersection — OpenAI/Azure Structured Outputs,
# Databricks ai_query responseFormat (additionalProperties:false, all-required,
# nullable collapsed, $ref inlined). Lossy by design.
weirding.to_json_schema(ir, strict=True)
```

Generated models are ordinary Pydantic `BaseModel` subclasses, so they drop straight into
LangChain/LangGraph `with_structured_output()` and provider tool definitions. The schema's
top-level `description` propagates to the class docstring so tool callers get a real
description.

End-to-end provider recipes live in the integration guides:

- [LangChain & LangGraph](docs/integrations/langchain.md)
- [OpenAI & Azure](docs/integrations/openai-azure.md)
- [Open-weight runtimes (vLLM / Ollama)](docs/integrations/open-weight.md)
- [Databricks & PySpark](docs/integrations/databricks-pyspark.md)

---

## LLM retry workflow

The `weirding.prompt` submodule provides provider-neutral helpers for structured-output
retry loops. They make **no API calls** and never echo input values (no PII leaks into retry
prompts) — they work with any provider, Claude included.

```python
import weirding
from weirding import prompt

Model = weirding.define_model("""
<Extraction>
  <entity type="string" required="true" description="Named entity from the text"/>
  <category type="string" required="true" description="PERSON, ORG, or LOC"/>
  <confidence type="number" required="true" minimum="0" maximum="1"/>
</Extraction>
""")

# Build an XML template to embed in the system prompt
system_prompt = f"Respond using exactly this XML format:\n\n{prompt.to_template(Model)}"

# Drive the retry loop
ctx = prompt.RetryContext(Model, max_attempts=3)
result = None
while not ctx.exceeded:
    message = "Extract entities from: ..."
    if ctx.attempt:
        message += "\n\n" + ctx.retry_message()  # built from format_error()
    llm_response = call_your_llm(system_prompt, message)
    try:
        result = weirding.parse(llm_response, Model)
        break
    except weirding.ParseError as exc:
        ctx.record_error(exc)
```

`prompt.format_error(error, model=...)` is also exposed directly if you manage the loop
yourself.

---

## `JsonSchemaIR` stability contract

`compile()` returns a public `JsonSchemaIR` dict. Changes to its format follow semantic
versioning ([ADR-0002](docs/adr/0002-json-schema-ir-as-public-api.md)):

- **Major** — removing or renaming existing keys.
- **Minor** — adding new optional keys, including new `x-weirding-*` extension keys.
- **No bump** — keys consumed only internally that never appear in `compile()` output.

---

## Documentation

- **Guide & API reference:** <https://yogs0ddhoth.github.io/weirding/>
- **Architecture decisions:** [`docs/adr/`](docs/adr/)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

---

## Contributing

Contributions are welcome. The workflow is standard git — never push directly to `main`:

```bash
git checkout -b feature/your-feature-name
# ... make changes ...
git push -u origin feature/your-feature-name
```

Then open a pull request.

**Development setup** (uses [`uv`](https://docs.astral.sh/uv/)):

```bash
uv sync --extra dev      # install
uv run pytest            # test
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pyright           # type check
```

Before opening a PR, run lint + tests and make sure both are clean — zero warnings, zero
failures. Read [`docs/adr/`](docs/adr/) before changing a component that has a recorded
decision.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`,
`fix:`, `docs:`, `refactor:`, `test:`, `chore:`, …); the type determines the version bump.

---

## License

[MIT](LICENSE) © Ben Lin
