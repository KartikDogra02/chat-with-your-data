import logging
from typing import Any

import openai
import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.config import get_settings
from backend.pipeline import answer_question
from backend.query_executor import QueryExecutionError
from backend.sql_generator import SQLGenerationError
from backend.sql_validator import UnsafeSQLError

logger = logging.getLogger(__name__)

app = FastAPI(title="Chat With Your Data")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"ping": "pong"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    question: str
    answer: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    attempts: int
    corrected: bool


@app.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest) -> AnswerResponse:
    answer = answer_question(request.question)

    return AnswerResponse(
        question=answer["question"],
        answer=answer["answer"],
        sql=answer["sql"],
        columns=answer["columns"],
        rows=answer["rows"],
        attempts=answer["attempts"],
        corrected=answer["corrected"],
    )


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.exception_handler(UnsafeSQLError)
def handle_unsafe_sql(request: Request, error: UnsafeSQLError) -> JSONResponse:
    return _error(400, f"The generated query was unsafe and was blocked: {error}")


@app.exception_handler(SQLGenerationError)
def handle_sql_generation_error(
    request: Request, error: SQLGenerationError
) -> JSONResponse:
    return _error(502, f"Could not generate SQL for this question: {error}")


@app.exception_handler(openai.OpenAIError)
def handle_openai_error(request: Request, error: openai.OpenAIError) -> JSONResponse:
    logger.exception("OpenAI request failed", exc_info=error)
    return _error(
        502, "The language model service is unavailable right now. Please try again."
    )


@app.exception_handler(QueryExecutionError)
def handle_query_execution_error(
    request: Request, error: QueryExecutionError
) -> JSONResponse:
    if isinstance(error.original_error, psycopg.errors.QueryCanceled):
        return _error(
            504,
            "The query took too long to run and was canceled. Try a narrower question.",
        )

    logger.info("Query failed even after a correction attempt: %s", error)
    return _error(
        400,
        "The generated query could not be run against the database. Try rephrasing your question.",
    )


@app.exception_handler(psycopg.OperationalError)
def handle_db_unavailable(
    request: Request, error: psycopg.OperationalError
) -> JSONResponse:
    logger.exception("Database connection failed", exc_info=error)
    return _error(503, "The database is currently unavailable. Please try again shortly.")


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled error while answering question", exc_info=error)
    return _error(500, "An unexpected error occurred. Please try again.")
