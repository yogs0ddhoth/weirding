# OpenAI & Azure OpenAI

OpenAI's and Azure OpenAI's Structured Outputs feature accepts a JSON Schema in `strict`
mode, but it requires a constrained subset: every object must set
`additionalProperties: false`, every property must be `required`, and several keywords are
disallowed. weirding's `to_json_schema(..., strict=True)` emits exactly the
OpenAI ∩ Databricks intersection, so the schema it returns is accepted unmodified by both
providers.

You author the schema once in XML, compile it, export the strict variant, and pass it as
`response_format`. Claude is one peer among providers here — the XML-authored schema is the
single source of truth and the strict export is the OpenAI/Azure-facing artifact.

## End-to-end

```python
import json
import weirding
from openai import OpenAI

SCHEMA_XML = """
<Invoice description="Structured fields extracted from an invoice">
  <vendor type="string" required="true"/>
  <total type="number" required="true"/>
  <currency type="string" required="true" enum="USD|EUR|GBP"/>
</Invoice>
"""

# XML schema -> IR -> strict provider schema
ir = weirding.compile(SCHEMA_XML)
schema = weirding.to_json_schema(ir, strict=True)

client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "Extract the invoice fields."},
        {"role": "user", "content": "Invoice from Acme Corp, total 1240.50 EUR."},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "Invoice",
            "schema": schema,
            "strict": True,
        },
    },
)

payload = resp.choices[0].message.content  # JSON string

# Validate the result back with the same weirding model
Invoice = weirding.from_schema(ir, name="Invoice")
invoice = Invoice.model_validate(json.loads(payload))
```

`from_schema(ir, ...)` reuses the IR you already compiled, so the validating model and the
provider schema come from one definition. If you prefer, validate with plain Pydantic by
constructing the model the same way.

## Azure OpenAI

Azure OpenAI exposes the identical Structured Outputs subset, so the same strict schema
works without changes — only the client construction differs:

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="https://<resource>.openai.azure.com",
    api_version="2024-08-01-preview",
    api_key="...",
)
# response_format payload is identical to the OpenAI example above
```

Which model deployments and API versions support Structured Outputs is a **caller concern**
— it is gated by your Azure deployment and the `api_version` you pin, not by weirding. Check
the Azure docs for the deployment/version matrix.

## Gotchas

- **Strict mode is lossy by design.** `to_json_schema(strict=True)` drops validation
  keywords the providers do not accept in strict mode (`minimum`, `maximum`, `pattern`,
  `format`, length/item bounds, `default`, and more), promotes every field to `required`,
  and collapses nullable fields to `{"type": [T, "null"]}`. Re-validate with the weirding
  model (or any full-strength JSON Schema validator) after parsing if you need those
  constraints enforced.
- **Unrepresentable constructs raise.** A nullable root, an `anyOf`/`oneOf`/`allOf` that is
  not a simple nullable, an unresolvable `$ref`, or a schema exceeding the 64-key cap raises
  `weirding.SchemaError` rather than emitting a schema the provider would reject. Fix the
  XML schema rather than working around the error.
