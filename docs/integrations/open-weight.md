# Open-weight models (vLLM, Ollama)

Open-weight serving stacks accept weirding's JSON Schema IR essentially as-is. The portable
artifact is the **clean** variant, `weirding.to_json_schema(ir)` (i.e. `strict=False`),
which strips weirding's internal `x-weirding-*` extension keys and returns plain JSON Schema
draft 2020-12 — valid input for vLLM and Ollama guided decoding and for the `jsonschema`
validator. For runtimes without guided decoding, fall back to the XML prompt template plus
weirding's parse/retry loop.

You author the schema in XML once; everything below consumes that single definition.

## vLLM (OpenAI-compatible structured outputs)

vLLM exposes an OpenAI-compatible server. Pass the clean schema through `response_format`'s
`json_schema`. The default `guided_decoding_backend=auto` lets vLLM pick a working backend
for the schema.

```python
import weirding
from openai import OpenAI

SCHEMA_XML = """
<Sentiment description="Sentiment classification of a customer message">
  <label type="string" required="true" enum="positive|neutral|negative"/>
  <score type="number" required="true" minimum="0" maximum="1"/>
</Sentiment>
"""

ir = weirding.compile(SCHEMA_XML)
schema = weirding.to_json_schema(ir)  # strict=False — clean draft 2020-12

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
resp = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    temperature=0,
    messages=[{"role": "user", "content": "I love this product!"}],
    response_format={
        "type": "json_schema",
        "json_schema": {"name": "Sentiment", "schema": schema},
    },
)
```

Recommend `temperature=0` for structured extraction. The clean (non-strict) schema is the
right choice for vLLM — it keeps the validation constraints (`minimum`/`maximum`/`enum`)
that strict mode would drop.

## Ollama

Ollama takes a JSON Schema directly in its `format` parameter. Pass the same clean schema.

```python
import weirding
import ollama

ir = weirding.compile(SCHEMA_XML)
schema = weirding.to_json_schema(ir)

resp = ollama.chat(
    model="llama3.1",
    messages=[{"role": "user", "content": "I love this product!"}],
    format=schema,
    options={"temperature": 0},
)
```

## Fallback: XML template + retry (no guided decoding)

Some runtimes have no guided/constrained decoding at all. For these, embed weirding's XML
template in the prompt and recover invalid output with `parse` + `RetryContext`. This is the
provider-neutral path that also underpins the Claude workflow.

```python
import weirding
from weirding import prompt

Sentiment = weirding.define_model(SCHEMA_XML)
template = prompt.to_template(Sentiment)

system = f"Classify the sentiment. Respond using exactly this XML format:\n\n{template}"

ctx = prompt.RetryContext(Sentiment, max_attempts=3)
result = None
while not ctx.exceeded:
    user_msg = "I love this product!"
    if ctx.attempt:
        user_msg += "\n\n" + ctx.retry_message()
    raw = call_your_runtime(system, user_msg)  # your inference call
    try:
        result = weirding.parse(raw, Sentiment)
        break
    except weirding.ParseError as exc:
        ctx.record_error(exc)

if result is None:
    raise RuntimeError("model did not produce valid output within max_attempts")
```

`format_error` / `RetryContext.retry_message()` deliberately omit the offending input
values (`include_input=False`), so the retry message is safe to send back to the model
without echoing user data.

## Gotchas

- **Nested `$ref` support varies.** Ollama and Llama-family grammar backends handle nested
  `$ref`/`$defs` unevenly. weirding's native-annotation compiler inlines nested objects and
  emits no `$ref`, so `to_json_schema(ir)` output is already flat for those schemas. If you
  build the IR yourself or use a dialect that emits `$ref` and your runtime struggles with
  it, use `to_json_schema(ir, strict=True)`, which inlines all local refs (at the cost of
  dropping constraints).
- **Recommend `temperature=0`** for deterministic structured extraction.
