# Getting Started

weirding is a production-grade Python library for XML ↔ Pydantic v2 conversion. It compiles
XML schema documents into Pydantic v2 `BaseModel` classes, validates XML data against those
models, and serializes instances back to XML. The XML schema you author once is a single
source of truth with first-class structured-output interop across the ecosystem — export
provider-ready schemas with `to_json_schema()` for OpenAI/Azure, Databricks `ai_query`, and
open-weight runtimes (vLLM/Ollama); drop generated models straight into LangChain/LangGraph;
and drive any provider's retry loop with the prompt utilities, Claude included. See the
[integration guides](integrations/langchain.md) for end-to-end recipes.

---

## Installation

Install the core library:

```bash
pip install weirding
```

For XSD schema support (optional):

```bash
pip install "weirding[xsd]"
```

---

## Core workflow

weirding uses a plain-attribute annotation convention. Define your schema as XML with `type`,
`required`, `description`, and other annotations on each field element:

```python
import weirding

schema_xml = """
<Response>
  <name type="string" required="true" description="Full name"/>
  <age type="integer" required="true" minimum="0"/>
  <bio type="string" required="false"/>
</Response>
"""

# Compile to JSON Schema IR (inspectable dict, follows JSON Schema draft 2020-12)
ir = weirding.compile(schema_xml)

# Compile directly to a Pydantic v2 BaseModel
Model = weirding.define_model(schema_xml)

# Parse XML data into a validated model instance
instance = weirding.parse("""
<Response>
  <name>Alice Smith</name>
  <age>30</age>
</Response>
""", Model)

# Serialize back to XML
xml_out = weirding.to_xml(instance)
```

The `compile()` → `define_model()` pipeline is idempotent and stateless — call it once at
startup and cache the result.

---

## XSD support

weirding auto-detects XSD schemas from the root element namespace. Install `weirding[xsd]`
and pass an XSD document to any of the core functions:

```python
import weirding

xsd_xml = """
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
"""

Model = weirding.define_model(xsd_xml)
instance = weirding.parse("<Person><name>Bob</name><age>25</age></Person>", Model)
```

---

## LLM retry workflow

weirding ships provider-neutral prompt engineering utilities for structured-output retry
loops — they make no API calls and work with any provider (Claude, OpenAI, open-weight, …).
`prompt.to_template()` turns a model into an XML prompt template, and `prompt.RetryContext`
manages the retry loop when the model returns invalid XML.

```python
import weirding
from weirding import prompt

schema_xml = """
<Extraction>
  <entity type="string" required="true" description="Named entity extracted from the text"/>
  <category type="string" required="true" description="Entity category: PERSON, ORG, or LOC"/>
  <confidence type="number" required="true" minimum="0" maximum="1"/>
</Extraction>
"""

Model = weirding.define_model(schema_xml)

# Build an XML template to embed in your LLM prompt
template = prompt.to_template(Model)
# => "<Extraction>\n  <entity>...</entity>\n  <category>...</category>\n  ..."

system_prompt = f"""Extract named entities from the user's text.
Respond using this XML format exactly:

{template}"""

# Retry loop — wraps the LLM call, parse, and error formatting
ctx = prompt.RetryContext(Model, max_attempts=3)

result = None
while not ctx.exceeded:
    user_message = "Extract entities from: ..."
    if ctx.attempt:
        # retry_message() is built from format_error() — safe to send back to the
        # model: no raw user data or PII is echoed (include_input=False)
        user_message += "\n\n" + ctx.retry_message()
    llm_response = call_your_llm(system_prompt, user_message)
    try:
        result = weirding.parse(llm_response, Model)
        break  # success
    except weirding.ParseError as exc:
        ctx.record_error(exc)
```

See the [API Reference](api.md) for full parameter documentation, and the
[integration guides](integrations/langchain.md) for provider-specific recipes.
