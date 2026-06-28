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
