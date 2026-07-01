# Chat With Your Data — Backend

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Install dependencies

From the repository root:

```bash
cd backend
uv sync
cp .env.example .env
```

The default environment file connects to the local PostgreSQL container defined in
`../docker-compose.yml`.

## Verify the database connection

Start PostgreSQL from the repository root:

```bash
docker compose up -d
```

Then, from the `backend` directory:

```bash
uv run python -m backend.db
```

The expected output is:

```text
Track count: 3503
```

## Run the development server

From the `backend` directory:

```bash
uv run uvicorn backend.main:app --reload
```

The API will be available at:

- Ping check: <http://127.0.0.1:8000/ping>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

Stop the server with `Ctrl+C`.

## Run development checks

```bash
uv run pytest
uv run ruff check .
uv run pyright
```

## Curl Example

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Which five artists generated the most sales?"}'
```

## Request logs

Each `/ask` call emits one structured JSON line (via the `backend.requests`
logger) that you'll see in the uvicorn output:

```json
{"event": "question_answered", "request_id": "5e5e63f7c9f2", "model": "gpt-4.1-mini",
 "schema_hash": "91385299c9ea", "refused": false, "attempts": 1, "corrected": false,
 "latency_ms": 3966.0, "input_tokens": 1411, "output_tokens": 34, "cost_usd": 0.0006188}
```

Failures log `{"event": "question_failed", "request_id": ..., "error_type": ...}`
instead. The raw question is never logged — only a 120-char `question_preview`
and a SHA-256 `question_hash`.
