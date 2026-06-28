from typing import Any

from openai import OpenAI

from backend.config import get_settings

SYSTEM_PROMPT = """\
You explain the result of a database query in plain language.

You are given the user's original question, the SQL that was run, and the rows it
returned. Write a short, direct answer to the question.

Rules:
- Answer the question directly in one or two sentences. No preamble.
- Lead with the single most important result and its figure.
- For a ranking, state the top result, then mention only the next one or two
  ("followed by ..."). Do not list every row or every number.
- Ground every claim in the returned rows. Never invent numbers or names.
- Format monetary amounts (sales, revenue, spend, price) with a leading $ and
  two decimal places, e.g. 138.6 -> $138.60.
- If there are no rows, say that no matching data was found.
- Do not mention SQL, tables, columns, or that a query was run.
"""


def _format_rows(columns: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "(no rows returned)"

    header = " | ".join(columns)
    body = "\n".join(" | ".join(str(value) for value in row) for row in rows)
    return f"{header}\n{body}"


def generate_answer(
    question: str,
    sql: str,
    columns: list[str],
    rows: list[list[Any]],
) -> str:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key or None)

    response = client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"SQL:\n{sql}\n\n"
                    f"Result:\n{_format_rows(columns, rows)}"
                ),
            }
        ],
    )

    return response.output_text.strip()


def main() -> None:
    answer = generate_answer(
        question="Which five artists have the most albums?",
        sql=(
            "SELECT ar.name AS artist_name, COUNT(al.album_id) AS album_count "
            "FROM artist ar JOIN album al ON al.artist_id = ar.artist_id "
            "GROUP BY ar.artist_id, ar.name "
            "ORDER BY album_count DESC, artist_name ASC LIMIT 5;"
        ),
        columns=["artist_name", "album_count"],
        rows=[
            ["Iron Maiden", 21],
            ["Led Zeppelin", 14],
            ["Deep Purple", 11],
            ["Metallica", 10],
            ["U2", 10],
        ],
    )
    print(answer)


if __name__ == "__main__":
    main()
