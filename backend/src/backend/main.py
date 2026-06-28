from dataclasses import dataclass
from typing import Any

from backend.pipeline import answer_question
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Chat With Your Data")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "chat_with_your_data.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]


@app.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest) -> AnswerResponse:
    answer = answer_question(request.question)

    return AnswerResponse(
        question=answer["question"],
        sql=answer["sql"],
        columns=answer["columns"],
        rows=answer["rows"],
    )