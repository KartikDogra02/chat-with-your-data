from openai import OpenAI
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.schema import format_schema, get_schema

SYSTEM_PROMPT = """\
You translate natural-language questions into a single PostgreSQL query.

Rules:
- Produce exactly one SQL statement that answers the question.
- The query MUST be read-only: a single SELECT. Never emit INSERT, UPDATE,
  DELETE, or any DDL/DML that modifies data or schema.
- Use only the tables and columns that appear in the provided schema."""


class SQLResponse(BaseModel):
    sql: str = Field(description="The read-only PostgreSQL SELECT query.")


def generate_sql(question: str, schema: str) -> str:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key or None)

    response = client.responses.parse(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": (
                    f"PostgreSQL schema:\n{schema}\n\n"
                    f"Question: {question}"
                ),
            }
        ],
        text_format=SQLResponse,
    )

    if response.output_parsed is None:
        raise RuntimeError("The model did not return a structured SQL response.")

    return response.output_parsed.sql


def main() -> None:
    schema = format_schema(get_schema())
    question = "Which five artists have the most albums?"
    print(generate_sql(question, schema))


if __name__ == "__main__":
    main()
