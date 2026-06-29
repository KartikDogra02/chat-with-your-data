from openai import OpenAI
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.schema import format_schema, get_schema

SYSTEM_PROMPT = """\
You translate natural-language questions into a single PostgreSQL query.

Rules:
- Produce exactly one SQL statement that answers the question.
- The query MUST be read-only: a single SELECT.
- Never emit INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or any other write operation.
- Use only the tables and columns that appear in the provided schema.
- Prefer explicit JOINs using the foreign key relationships in the schema.
- Use clear column aliases for computed values.
- When the user asks for "top", "most", "highest", or "best", use ORDER BY and LIMIT.
- If aggregating, include the correct GROUP BY columns.
- SELECT only the columns needed to directly answer the question. Do NOT add
  primary key / ID columns or extra descriptive columns unless the question asks
  for them.
- When identifying a person or entity by name, return a single display column.
  Concatenate component name columns (e.g. first and last name) into one column
  separated by a space, rather than selecting them separately.
- Make ordering deterministic: when sorting by a value that can tie, add a
  secondary ORDER BY on a name or id column to break ties.
- Distinguish counts from money. "How many tracks were sold" / "units sold" is a
  count of units: SUM(invoice_line.quantity). Monetary "sales", "revenue", or
  "spend" is an amount: SUM(invoice_line.unit_price * invoice_line.quantity).
- Beware join fan-out when aggregating money. To attribute monetary
  sales/revenue to an entity below the invoice grain (track, album, artist, or
  genre), sum the line-item amount (invoice_line.unit_price *
  invoice_line.quantity). Do NOT sum invoice.total in that case — it covers the
  whole invoice and is duplicated across every joined line, which overcounts.
"""


class SQLGenerationError(RuntimeError):
    """Raised when the model fails to produce a usable SQL response."""


class SQLResponse(BaseModel):
    sql: str = Field(description="The read-only PostgreSQL SELECT query.")


FIX_SYSTEM_PROMPT = """\
You repair a PostgreSQL query that failed to execute.

You are given the user's original question, the database schema, the SQL
that was attempted, and the database error it raised. Return one corrected
query that answers the question without raising that error.

Rules:
- Return exactly one SQL statement.
- It must be read-only: a single SELECT. Never emit INSERT, UPDATE, DELETE,
  DROP, ALTER, CREATE, or any other write operation.
- Use only the tables and columns that appear in the provided schema.
- Prefer changing as little as needed to fix the error.
"""


def generate_sql(question: str, schema: str) -> str:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key or None)

    response = client.responses.parse(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": f"PostgreSQL schema:\n{schema}\n\nQuestion: {question}",
            }
        ],
        text_format=SQLResponse,
    )

    if response.output_parsed is None:
        raise SQLGenerationError("The model did not return a structured SQL response.")

    return response.output_parsed.sql


def fix_sql(question: str, schema: str, bad_sql: str, error_message: str) -> str:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key or None)

    content = (
        f"The previous SQL failed.\n\n"
        f"Question:\n{question}\n\n"
        f"Schema:\n{schema}\n\n"
        f"Failed SQL:\n{bad_sql}\n\n"
        f"Database error:\n{error_message}\n\n"
        f"Return one corrected PostgreSQL SELECT query."
    )

    response = client.responses.parse(
        model=settings.openai_model,
        instructions=FIX_SYSTEM_PROMPT,
        input=[{"role": "user", "content": content}],
        text_format=SQLResponse,
    )

    if response.output_parsed is None:
        raise SQLGenerationError("The model did not return a structured SQL response.")

    return response.output_parsed.sql


def main() -> None:
    schema = format_schema(get_schema())
    question = "Which five artists have the most albums?"
    print(generate_sql(question, schema))


if __name__ == "__main__":
    main()
