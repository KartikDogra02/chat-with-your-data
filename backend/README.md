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

- Health check: <http://127.0.0.1:8000/health>
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
