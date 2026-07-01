"""LLM-as-judge for the plain-English answer.

The exact-row eval checks the SQL returned the right data. This checks a
different thing: does the prose answer faithfully describe the rows it was
given? The two can disagree (right rows, sloppy summary — or vice versa), which
is exactly why it's a separate, optional signal.
"""

from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.metrics import TokenUsage, token_usage_from

JUDGE_SYSTEM_PROMPT = """\
You check whether a plain-English answer faithfully reflects the data it was
based on.

You are given the user's question, the data that was returned (columns and
rows), and the answer that was written from it. Set correct=true only if:
- every factual claim in the answer (names, numbers, rankings) is supported by
  the rows, and
- the answer actually addresses the question.

Otherwise set correct=false and give a one-sentence reason. Do not require the
answer to mention every row — a good answer can summarize.
"""


class JudgeResponse(BaseModel):
    correct: bool = Field(description="True if the answer faithfully reflects the data.")
    reason: str = Field(description="One sentence justifying the verdict.")


def _format_rows(columns: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "(no rows returned)"
    header = " | ".join(columns)
    body = "\n".join(" | ".join(str(value) for value in row) for row in rows)
    return f"{header}\n{body}"


def judge_answer(
    question: str,
    columns: list[str],
    rows: list[list[Any]],
    answer: str,
    model: str | None = None,
) -> tuple[bool, str, TokenUsage]:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key or None)

    content = (
        f"Question:\n{question}\n\n"
        f"Data:\n{_format_rows(columns, rows)}\n\n"
        f"Answer:\n{answer}"
    )

    response = client.responses.parse(
        model=model or settings.openai_model,
        instructions=JUDGE_SYSTEM_PROMPT,
        input=[{"role": "user", "content": content}],
        text_format=JudgeResponse,
    )

    parsed = response.output_parsed
    if parsed is None:
        # Judge failed to produce a verdict — treat as inconclusive-but-not-pass.
        return False, "Judge did not return a structured verdict.", token_usage_from(response)

    return parsed.correct, parsed.reason, token_usage_from(response)
