from typing import Any

import pytest

from backend import pipeline
from backend.metrics import TokenUsage
from backend.query_executor import QueryExecutionError, QueryResult
from backend.sql_generator import SQLGenerationError, SQLResponse
from backend.sql_validator import UnsafeSQLError

# Passed to answer_question in every test so it never falls back to get_settings
# (keeps these tests independent of .env / a live database).
TEST_MODEL = "test-model"


def _answer(question: str) -> dict:
    return pipeline.answer_question(question, model=TEST_MODEL)


def test_answer_question_returns_first_successful_query(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema, model: (
            SQLResponse(can_answer=True, sql="SELECT 1;"),
            TokenUsage(10, 5),
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "execute_query",
        lambda sql: QueryResult(columns=["value"], rows=[[1]]),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, sql, columns, rows, model: (
            "The answer is 1.",
            TokenUsage(20, 8),
        ),
    )

    answer = _answer("What is the answer?")

    assert answer["sql"] == "SELECT 1;"
    assert answer["columns"] == ["value"]
    assert answer["rows"] == [[1]]
    assert answer["attempts"] == 1
    assert answer["corrected"] is False
    assert answer["refused"] is False
    # Token usage is summed across the two model calls.
    assert answer["metrics"]["input_tokens"] == 30
    assert answer["metrics"]["output_tokens"] == 13


def test_answer_question_retries_failed_sql_once(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    def fake_execute_query(sql: str) -> QueryResult:
        calls.append(sql)
        if sql == "SELECT * FROM artists;":
            raise QueryExecutionError(
                sql,
                RuntimeError('relation "artists" does not exist'),
            )
        return QueryResult(columns=["name"], rows=[["Iron Maiden"]])

    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema, model: (
            SQLResponse(can_answer=True, sql="SELECT * FROM artists;"),
            TokenUsage(),
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "fix_sql",
        lambda question, schema, bad_sql, error_message, model: (
            "SELECT name FROM artist;",
            TokenUsage(),
        ),
    )
    monkeypatch.setattr(pipeline, "execute_query", fake_execute_query)
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, sql, columns, rows, model: (
            "Iron Maiden matched.",
            TokenUsage(),
        ),
    )

    answer = _answer("Show me an artist.")

    assert calls == ["SELECT * FROM artists;", "SELECT name FROM artist;"]
    assert answer["sql"] == "SELECT name FROM artist;"
    assert answer["rows"] == [["Iron Maiden"]]
    assert answer["attempts"] == 2
    assert answer["corrected"] is True
    assert answer["refused"] is False


def test_answer_question_raises_clearly_when_correction_also_fails(
    monkeypatch: Any,
) -> None:
    fix_sql_calls: list[str] = []

    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema, model: (
            SQLResponse(can_answer=True, sql="SELECT * FROM artists;"),
            TokenUsage(),
        ),
    )

    def fake_fix_sql(
        question: str, schema: str, bad_sql: str, error_message: str, model: str
    ) -> tuple[str, TokenUsage]:
        fix_sql_calls.append(bad_sql)
        return "SELECT * FROM artistsss;", TokenUsage()

    monkeypatch.setattr(pipeline, "fix_sql", fake_fix_sql)
    monkeypatch.setattr(
        pipeline,
        "execute_query",
        lambda sql: (_ for _ in ()).throw(
            QueryExecutionError(sql, RuntimeError("still broken"))
        ),
    )

    with pytest.raises(QueryExecutionError):
        _answer("Show me an artist.")

    # Exactly one correction attempt: no unbounded retry loop.
    assert len(fix_sql_calls) == 1


def test_answer_question_does_not_correct_unsafe_sql(monkeypatch: Any) -> None:
    fix_sql_calls: list[str] = []

    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema, model: (
            SQLResponse(can_answer=True, sql="DELETE FROM track;"),
            TokenUsage(),
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "fix_sql",
        lambda question, schema, bad_sql, error_message, model: (
            fix_sql_calls.append(bad_sql),
            TokenUsage(),
        ),
    )

    def fake_execute_query(sql: str) -> QueryResult:
        raise UnsafeSQLError("SQL must be read-only.")

    monkeypatch.setattr(pipeline, "execute_query", fake_execute_query)

    with pytest.raises(UnsafeSQLError):
        _answer("Delete all tracks.")

    # Validation failures are not execution failures: no correction attempt.
    assert fix_sql_calls == []


def test_answer_question_refuses_impossible_question(monkeypatch: Any) -> None:
    execute_calls: list[str] = []

    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema, model: (
            SQLResponse(
                can_answer=False,
                reason="The schema has no refund data.",
            ),
            TokenUsage(12, 6),
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "execute_query",
        lambda sql: execute_calls.append(sql),
    )

    answer = _answer("What was the refund rate last month?")

    # A refusal never touches the database or generates an answer from rows.
    assert execute_calls == []
    assert answer["refused"] is True
    assert answer["sql"] is None
    assert answer["rows"] == []
    assert answer["columns"] == []
    assert answer["answer"] == "The schema has no refund data."
    assert answer["attempts"] == 1
    assert answer["corrected"] is False


def test_answer_question_raises_when_can_answer_but_no_sql(monkeypatch: Any) -> None:
    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    # A malformed structured response: says it can answer but omits the SQL.
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema, model: (
            SQLResponse(can_answer=True, sql=None),
            TokenUsage(),
        ),
    )

    with pytest.raises(SQLGenerationError):
        _answer("Show me an artist.")
