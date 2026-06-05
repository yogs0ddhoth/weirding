# Databricks & PySpark

weirding fits two Databricks patterns for structured LLM output over Spark DataFrames: the
native `ai_query` SQL/Python function, and a bring-your-own-client batch UDF. Both consume
a schema you author once in XML. Databricks `ai_query`'s `responseFormat` is the strictest
schema consumer weirding targets, and `weirding.to_json_schema(ir, strict=True)` produces
exactly the OpenAI ∩ Databricks intersection it accepts.

!!! danger "Privacy: never log raw inputs or full responses"
    Every example here logs only **validation outcomes and counts** — never raw row inputs
    or full LLM responses. In Spark, a `print`/`logger.info` of row data writes user content
    to **executor logs and the Spark UI**, keyed by partition, where it persists outside
    your control. This is a privacy violation under weirding's no-PII-in-logs policy
    (MEMORY.md rule 2, ETHOS.md "privacy by architecture").

    Note specifically that `prompt.format_error` and `RetryContext.retry_message()` describe
    *which fields* failed and *why*, and their messages can embed offending field values in
    some validator messages. **Do not persist `format_error` / `RetryContext` output to
    logs or to a DataFrame column.** Send it back to the model in-memory for the retry only.
    `format_error` already runs with `include_input=False` to minimize this exposure, but
    treat its output as potentially user-derived regardless.

## Pattern A — native `ai_query`

Use the strict export as the `responseFormat` JSON schema. Strict mode produces the
Databricks-valid intersection (`additionalProperties:false`, all-`required`, nullable
collapsed to `[T,"null"]`, refs inlined, unsupported keywords stripped).

```python
import json
import weirding
from pyspark.sql import functions as F

SCHEMA_XML = """
<Triage description="Support ticket triage result">
  <priority type="string" required="true" enum="low|medium|high"/>
  <category type="string" required="true"/>
</Triage>
"""

ir = weirding.compile(SCHEMA_XML)
schema = weirding.to_json_schema(ir, strict=True)
response_format = json.dumps({
    "type": "json_schema",
    "json_schema": {"name": "Triage", "schema": schema, "strict": True},
})

df = spark.table("support_tickets")  # noqa: F821 (Databricks-provided)
result = df.withColumn(
    "triage",
    F.expr(
        "ai_query("
        "  'databricks-meta-llama-3-3-70b-instruct',"
        "  request => body,"
        f"  responseFormat => '{response_format}',"
        "  failOnError => false"  # do not fail the whole job on one bad row
        ")"
    ),
)
```

**Caveats:**

- **64-key cap.** `ai_query` schemas are limited to 64 total keys.
  `to_json_schema(strict=True)` raises `weirding.SchemaError` if the transformed schema
  exceeds this, rather than emitting a schema Databricks would reject — keep your schema
  small.
- **No per-row retry.** `ai_query` has no built-in retry. Use `failOnError => false` so a
  single malformed row yields a null/error column instead of failing the job, then handle
  failures downstream. Inspect counts of failed rows — not their contents.

## Pattern B — BYO client in a batch UDF

When you call an LLM client yourself (custom endpoint, retry policy, your own provider), run
it inside a `pandas_udf` or `mapInPandas`. The key constraint is **executor serialization**.

### Build the model inside the UDF closure

weirding builds models dynamically via `type(...)`, so the **class object cannot be pickled
by qualified name** and shipped driver → executor. Build it **inside the partition closure**
instead. `define_model(...)` is cheap for 1–50KB payloads, so compiling once per partition
is negligible.

```python
import pandas as pd
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType

SCHEMA_XML = """..."""  # the XML schema string is picklable; the model class is not
MAX_RETRIES = 3         # HARD cap — see speculative-execution note below

@pandas_udf(StringType())
def triage_udf(messages: pd.Series) -> pd.Series:
    import weirding
    from weirding import prompt

    # Build the model PER PARTITION, inside the closure — never serialize the class.
    Triage = weirding.define_model(SCHEMA_XML)

    out: list[str | None] = []
    ok = 0
    failed = 0
    for raw_text in messages:
        ctx = prompt.RetryContext(Triage, max_attempts=MAX_RETRIES)
        validated = None
        while not ctx.exceeded:                      # bounded by MAX_RETRIES
            user_msg = raw_text
            if ctx.attempt:
                # retry_message stays in memory for the model only — never logged
                user_msg = raw_text + "\n\n" + ctx.retry_message()
            response = call_your_llm(user_msg)       # your client call
            try:
                validated = weirding.parse(response, Triage)
                break
            except weirding.ParseError as exc:
                ctx.record_error(exc)                # do NOT log exc / its message
        if validated is not None:
            ok += 1
            out.append(validated.model_dump_json())
        else:
            failed += 1
            out.append(None)
    # PRIVACY-SAFE: log counts only, never row text or responses
    # logger.info("partition done: ok=%d failed=%d", ok, failed)  # counts only
    return pd.Series(out)

df = spark.table("support_tickets")  # noqa: F821
result = df.withColumn("triage_json", triage_udf(df["body"]))
```

**Why the hard retry cap matters:** Spark **speculative execution** can launch duplicate
task attempts for slow partitions. Unbounded retries inside a UDF amplify this — duplicate
attempts each burn the full retry budget, multiplying LLM calls and cost. Always cap retries
(`MAX_RETRIES` above) and prefer idempotent handling.

Recommend **`pydantic>=2.5`** on the cluster for stable model-construction behavior in the
executor environment.

### Pydantic → Spark `StructType`

If you need a typed Spark `StructType` (rather than a JSON string column) from the
weirding-generated model, delegate to **[`sparkdantic`](https://pypi.org/project/sparkdantic/)**:

```python
from sparkdantic import create_spark_schema

Triage = weirding.define_model(SCHEMA_XML)
struct_type = create_spark_schema(Triage)  # StructType for use with from_json / schemas
```

weirding intentionally does **not** add a PySpark dependency — that would re-introduce a
binary-compatibility liability on the cluster (MEMORY.md rule 6). `sparkdantic` is the
right place for the Pydantic → Spark mapping.

## Gotchas summary

- Build the weirding model **inside** the UDF/partition closure; never serialize the class.
- Cap retries hard; speculative execution can duplicate task attempts.
- Log **counts only** — never row inputs, LLM responses, or `format_error`/`retry_message`
  output.
- `ai_query` has no per-row retry; use `failOnError => false`.
- Strict-mode schemas are capped at 64 keys (raises `SchemaError` if exceeded).
- Delegate `StructType` generation to `sparkdantic`; weirding adds no PySpark dependency.
