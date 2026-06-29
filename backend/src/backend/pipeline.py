import sys

from backend.answer_generator import generate_answer
from backend.query_executor import QueryExecutionError, execute_query
from backend.schema import format_schema, get_schema
from backend.sql_generator import fix_sql, generate_sql


def answer_question(question: str):
    schema = format_schema(get_schema())

    sql = generate_sql(question=question, schema=schema)
    attempts = 1
    corrected = False

    try:
        result = execute_query(sql)
    except QueryExecutionError as error:
        sql = fix_sql(
            question=question,
            schema=schema,
            bad_sql=error.sql,
            error_message=str(error.original_error),
        )
        result = execute_query(sql)
        attempts += 1
        corrected = True

    answer = generate_answer(
        question=question,
        sql=sql,
        columns=result.columns,
        rows=result.rows,
    )

    return {
        "question": question,
        "answer": answer,
        "sql": sql,
        "columns": result.columns,
        "rows": result.rows,
        "attempts": attempts,
        "corrected": corrected,
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

    print("\nSQL:")
    print(answer["sql"])

    print("\nResult:")
    print(answer["columns"])
    for row in answer["rows"]:
        print(row)

    print(f"\nAttempts: {answer['attempts']} (corrected: {answer['corrected']})")


if __name__ == "__main__":
    main()
