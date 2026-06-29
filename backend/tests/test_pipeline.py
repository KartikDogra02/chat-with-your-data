from typing import Any

import pytest

from backend import pipeline
from backend.query_executor import QueryExecutionError, QueryResult
from backend.sql_validator import UnsafeSQLError


def test_answer_question_returns_first_successful_query(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(pipeline, "generate_sql", lambda question, schema: "SELECT 1;")
    monkeypatch.setattr(
        pipeline,
        "execute_query",
        lambda sql: QueryResult(columns=["value"], rows=[[1]]),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, sql, columns, rows: "The answer is 1.",
    )

    answer = pipeline.answer_question("What is the answer?")

    assert answer["sql"] == "SELECT 1;"
    assert answer["columns"] == ["value"]
    assert answer["rows"] == [[1]]
    assert answer["attempts"] == 1
    assert answer["corrected"] is False


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
        lambda question, schema: "SELECT * FROM artists;",
    )
    monkeypatch.setattr(
        pipeline,
        "fix_sql",
        lambda question, schema, bad_sql, error_message: "SELECT name FROM artist;",
    )
    monkeypatch.setattr(pipeline, "execute_query", fake_execute_query)
    monkeypatch.setattr(
        pipeline,
        "generate_answer",
        lambda question, sql, columns, rows: "Iron Maiden matched.",
    )

    answer = pipeline.answer_question("Show me an artist.")

    assert calls == ["SELECT * FROM artists;", "SELECT name FROM artist;"]
    assert answer["sql"] == "SELECT name FROM artist;"
    assert answer["rows"] == [["Iron Maiden"]]
    assert answer["attempts"] == 2
    assert answer["corrected"] is True


def test_answer_question_raises_clearly_when_correction_also_fails(
    monkeypatch: Any,
) -> None:
    fix_sql_calls: list[str] = []

    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema: "SELECT * FROM artists;",
    )

    def fake_fix_sql(question: str, schema: str, bad_sql: str, error_message: str) -> str:
        fix_sql_calls.append(bad_sql)
        return "SELECT * FROM artistsss;"

    monkeypatch.setattr(pipeline, "fix_sql", fake_fix_sql)
    monkeypatch.setattr(
        pipeline,
        "execute_query",
        lambda sql: (_ for _ in ()).throw(
            QueryExecutionError(sql, RuntimeError("still broken"))
        ),
    )

    with pytest.raises(QueryExecutionError):
        pipeline.answer_question("Show me an artist.")

    # Exactly one correction attempt: no unbounded retry loop.
    assert len(fix_sql_calls) == 1


def test_answer_question_does_not_correct_unsafe_sql(monkeypatch: Any) -> None:
    fix_sql_calls: list[str] = []

    monkeypatch.setattr(pipeline, "get_schema", lambda: [])
    monkeypatch.setattr(pipeline, "format_schema", lambda schema: "schema")
    monkeypatch.setattr(
        pipeline,
        "generate_sql",
        lambda question, schema: "DELETE FROM track;",
    )
    monkeypatch.setattr(
        pipeline,
        "fix_sql",
        lambda question, schema, bad_sql, error_message: fix_sql_calls.append(bad_sql),
    )

    def fake_execute_query(sql: str) -> QueryResult:
        raise UnsafeSQLError("SQL must be read-only.")

    monkeypatch.setattr(pipeline, "execute_query", fake_execute_query)

    with pytest.raises(UnsafeSQLError):
        pipeline.answer_question("Delete all tracks.")

    # Validation failures are not execution failures: no correction attempt.
    assert fix_sql_calls == []
