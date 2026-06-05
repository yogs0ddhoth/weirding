# LangChain & LangGraph

weirding produces ordinary Pydantic v2 models, so it composes with LangChain and LangGraph
with no adapter. You author your schema once in XML, compile it to a model, and hand that
model to LangChain's structured-output and state APIs exactly as you would a hand-written
`BaseModel`. Claude is one of many chat models this works with — the same code runs against
any LangChain `BaseChatModel` that supports `with_structured_output`.

## Structured output

`define_model(...)` returns a `type[BaseModel]`. Pass it straight to
`with_structured_output` — no wrapping required.

```python
import weirding
from langchain_anthropic import ChatAnthropic  # or any BaseChatModel

SCHEMA_XML = """
<Extraction description="Named entities extracted from a document">
  <entity type="string" required="true" description="The named entity"/>
  <category type="string" required="true" enum="PERSON|ORG|LOC"
            description="Entity category"/>
  <confidence type="number" required="true" minimum="0" maximum="1"/>
</Extraction>
"""

Extraction = weirding.define_model(SCHEMA_XML)

llm = ChatAnthropic(model="claude-sonnet-4-5")
structured = llm.with_structured_output(Extraction)

result = structured.invoke("Acme Corp announced a partnership with Jane Doe in Berlin.")
# result is an Extraction instance
```

### Tool descriptions now populate

LangChain derives the tool/function description it sends to the provider from the model's
`__doc__`. As of weirding's Phase 2 change, a generated model carries the schema's
top-level `description` attribute into `Model.__doc__`, so the example above sends
`"Named entities extracted from a document"` as the tool description instead of an empty
string. Always set a `description` on the root element — it materially improves tool-calling
accuracy.

## LangGraph Pydantic state

A weirding model works as a LangGraph state channel or as a typed field inside a larger
state schema, because LangGraph serializes state through Pydantic.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class GraphState(TypedDict):
    text: str
    extraction: Extraction  # weirding-generated model as a typed state field

def extract_node(state: GraphState) -> dict:
    out = structured.invoke(state["text"])
    return {"extraction": out}

builder = StateGraph(GraphState)
builder.add_node("extract", extract_node)
builder.set_entry_point("extract")
builder.add_edge("extract", END)
graph = builder.compile()

final = graph.invoke({"text": "Acme Corp partnered with Jane Doe in Berlin."})
```

## Gotchas

### OpenAI strict mode

When the underlying model is OpenAI's, `with_structured_output` defaults to the
`json_schema` strict path, which rejects schemas that are not fully strict-compliant (every
object needs `additionalProperties: false` and all-`required`, and several keywords are
disallowed). If a weirding model trips this, use the function-calling escape hatch:

```python
structured = llm.with_structured_output(Extraction, method="function_calling")
```

For a first-class strict-mode schema, export it explicitly with
`weirding.to_json_schema(weirding.compile(SCHEMA_XML), strict=True)` and supply it through
the provider's native `response_format` (see the
[OpenAI & Azure guide](openai-azure.md)). Note that strict mode is lossy — it drops
constraints such as `minimum`/`maximum`/`pattern`.

### Nested `$ref` with Ollama / Llama-family runtimes

Some open-weight runtimes (Ollama, Llama.cpp grammars) handle nested `$ref`/`$defs`
unevenly. weirding's native-annotation compiler inlines nested objects and emits no
`$ref`, so models from `define_model(...)` are safe. If you build the IR yourself or use a
dialect that emits `$ref`, export with `weirding.to_json_schema(ir, strict=True)`, which
inlines all local refs. See the [open-weight guide](open-weight.md).

### LangGraph checkpointing and the dynamic class

weirding builds models dynamically (via `type(...)`), so the **class object** is not
picklable by qualified name across a process boundary. State **instances** serialize fine
(LangGraph dumps them as field data), so single-process checkpointing works. If you need
cross-process class transport — distributed workers that must reconstruct the type by
import path — define the model at **module scope** (so it has a stable import path) or
rebuild it inside the graph-build step on each worker. Do not pass the class itself through
a checkpointer.

```python
# module scope — stable import path for cross-process workers
Extraction = weirding.define_model(SCHEMA_XML)
```
