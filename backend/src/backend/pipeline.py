import hashlib
import sys
import time

from backend.answer_generator import generate_answer
from backend.config import get_settings
from backend.metrics import TokenUsage
from backend.pricing import cost_usd
from backend.query_executor import QueryExecutionError, execute_query
from backend.schema import format_schema, get_schema
from backend.sql_generator import SQLGenerationError, fix_sql, generate_sql

REFUSAL_FALLBACK = "I can't answer that from the available schema."


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _schema_hash(schema: str) -> str:
    # A short fingerprint of the exact schema text sent to the model. Lets logs
    # tie a request to the prompt context it ran against, so a change in schema
    # (or how we format it) is visible without logging the whole thing.
    return hashlib.sha256(schema.encode()).hexdigest()[:12]


def _metrics(
    model: str, usage: TokenUsage, timings_ms: dict[str, float], schema_hash: str
) -> dict:
    timings_ms["total"] = round(sum(timings_ms.values()), 1)
    return {
        "model": model,
        "schema_hash": schema_hash,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": cost_usd(model, usage.input_tokens, usage.output_tokens),
        "timings_ms": timings_ms,
    }


def answer_question(question: str, model: str | None = None):
    model = model or get_settings().openai_model
    usage = TokenUsage()

    start = time.perf_counter()
    schema = format_schema(get_schema())
    t_schema = _ms(start)
    schema_hash = _schema_hash(schema)

    start = time.perf_counter()
    decision, u = generate_sql(question=question, schema=schema, model=model)
    usage += u
    t_generate = _ms(start)

    # The model declined: the question can't be answered from the schema. Return
    # the reason without touching the database.
    if not decision.can_answer:
        return {
            "question": question,
            "answer": decision.reason or REFUSAL_FALLBACK,
            "sql": None,
            "columns": [],
            "rows": [],
            "attempts": 1,
            "corrected": False,
            "refused": True,
            "metrics": _metrics(
                model,
                usage,
                {"schema": t_schema, "generate_sql": t_generate},
                schema_hash,
            ),
        }

    # can_answer is true, so sql should be present. Guard the malformed case
    # (also narrows the type from str | None to str for what follows).
    sql = decision.sql
    if sql is None:
        raise SQLGenerationError(
            "The model reported the question is answerable but returned no SQL."
        )

    attempts = 1
    corrected = False
    t_fix = 0.0

    start = time.perf_counter()
    try:
        result = execute_query(sql)
    except QueryExecutionError as error:
        t_execute = _ms(start)

        start = time.perf_counter()
        sql, u = fix_sql(
            question=question,
            schema=schema,
            bad_sql=error.sql,
            error_message=str(error.original_error),
            model=model,
        )
        usage += u
        t_fix = _ms(start)

        start = time.perf_counter()
        result = execute_query(sql)
        t_execute += _ms(start)
        attempts += 1
        corrected = True
    else:
        t_execute = _ms(start)

    start = time.perf_counter()
    answer, u = generate_answer(
        question=question,
        sql=sql,
        columns=result.columns,
        rows=result.rows,
        model=model,
    )
    usage += u
    t_answer = _ms(start)

    return {
        "question": question,
        "answer": answer,
        "sql": sql,
        "columns": result.columns,
        "rows": result.rows,
        "attempts": attempts,
        "corrected": corrected,
        "refused": False,
        "metrics": _metrics(
            model,
            usage,
            {
                "schema": t_schema,
                "generate_sql": t_generate,
                "execute": t_execute,
                "fix_sql": t_fix,
                "answer": t_answer,
            },
            schema_hash,
        ),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Please provide a question.\n"
            'Example: uv run python -m backend.pipeline "Which five artists generated the most sales?"'
        )

    question = " ".join(sys.argv[1:])
    answer = answer_question(question)

    print("Question:")
    print(answer["question"])

    print("\nAnswer:")
    print(answer["answer"])

    if answer["refused"]:
        print("\n(refused: no SQL was run)")
    else:
        print("\nSQL:")
        print(answer["sql"])

        print("\nResult:")
        print(answer["columns"])
        for row in answer["rows"]:
            print(row)

        print(f"\nAttempts: {answer['attempts']} (corrected: {answer['corrected']})")

    metrics = answer["metrics"]
    print(
        f"\nMetrics: {metrics['timings_ms']['total']}ms total, "
        f"{metrics['input_tokens']}+{metrics['output_tokens']} tokens, "
        f"cost ~${metrics['cost_usd']:.5f}"
        if metrics["cost_usd"] is not None
        else f"\nMetrics: {metrics['timings_ms']['total']}ms total, "
        f"{metrics['input_tokens']}+{metrics['output_tokens']} tokens"
    )


if __name__ == "__main__":
    main()
