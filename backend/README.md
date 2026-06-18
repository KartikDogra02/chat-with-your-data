# Chat With Your Data — Backend

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Install dependencies

From the repository root:

```bash
cd backend
uv sync
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
