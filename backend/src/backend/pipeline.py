import sys

from backend.schema import get_schema, format_schema
from backend.sql_generator import generate_sql
from backend.query_executor import execute_query


def answer_question(question: str):
    schema = format_schema(get_schema())
    sql = generate_sql(question=question, schema=schema)
    result = execute_query(sql)

    return {
        "question": question,
        "sql": sql,
        "columns": result.columns,
        "rows": result.rows,
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

    print("\nSQL:")
    print(answer["sql"])

    print("\nResult:")
    print(answer["columns"])
    for row in answer["rows"]:
        print(row)


if __name__ == "__main__":
    main()