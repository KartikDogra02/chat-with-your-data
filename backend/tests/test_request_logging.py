"""Tests for the structured /ask request logs.

Importing backend.main constructs the app, which reads settings (for CORS) at
import time. Set a dummy DATABASE_URL first so this runs without a .env — the
pipeline is mocked, so nothing ever connects.
"""

import json
import logging
import os
from typing import Any

os.environ.setdefault("DATABASE_URL", "postgresql://test/none")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.main as main  # noqa: E402
from backend.query_executor import QueryExecutionError  # noqa: E402

ANSWERED = {
    "question": "how many tracks?",
    "answer": "There are 3503 tracks.",
    "sql": "SELECT COUNT(*) FROM track;",
    "columns": ["track_count"],
    "rows": [[3503]],
    "attempts": 1,
    "corrected": False,
    "refused": False,
    "metrics": {
        "model": "gpt-4.1-mini",
        "schema_hash": "abc123def456",
        "input_tokens": 100,
        "output_tokens": 10,
        "cost_usd": 0.0005,
        "timings_ms": {"total": 1234.5},
    },
}


@pytest.fixture
def captured_logs() -> Any:
    """Capture request_logger output directly (it has propagate=False)."""
    messages: list[str] = []
    handler = logging.Handler()
    handler.emit = lambda record: messages.append(record.getMessage())
    main.request_logger.addHandler(handler)
    try:
        yield messages
    finally:
        main.request_logger.removeHandler(handler)


def test_ask_logs_question_answered(monkeypatch: Any, captured_logs: list[str]) -> None:
    monkeypatch.setattr(main, "answer_question", lambda question: ANSWERED)

    response = TestClient(main.app).post("/ask", json={"question": "how many tracks?"})
    assert response.status_code == 200

    payload = json.loads(captured_logs[-1])
    assert payload["event"] == "question_answered"
    assert payload["model"] == "gpt-4.1-mini"
    assert payload["schema_hash"] == "abc123def456"
    assert payload["refused"] is False
    assert payload["latency_ms"] == 1234.5
    assert payload["input_tokens"] == 100
    assert payload["cost_usd"] == 0.0005
    # The raw question is not logged in full — only a preview + hash.
    assert payload["question_preview"] == "how many tracks?"
    assert len(payload["question_hash"]) == 64
    assert "question" not in payload  # no full-question field


def test_ask_logs_question_failed(monkeypatch: Any, captured_logs: list[str]) -> None:
    def boom(question: str) -> dict:
        raise QueryExecutionError("SELECT 1", RuntimeError("nope"))

    monkeypatch.setattr(main, "answer_question", boom)

    # The registered handler turns QueryExecutionError into a 400 response.
    response = TestClient(main.app).post("/ask", json={"question": "boom"})
    assert response.status_code == 400

    failed = [json.loads(m) for m in captured_logs if '"question_failed"' in m]
    assert failed, "expected a question_failed log line"
    assert failed[-1]["event"] == "question_failed"
    assert failed[-1]["error_type"] == "QueryExecutionError"
    assert failed[-1]["question_preview"] == "boom"
