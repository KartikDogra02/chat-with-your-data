# Chat With Your Data

Live demo: https://chat-with-your-data-frontend.onrender.com

Ask a plain-English question about a database and get back a grounded answer,
the SQL that produced it, and a chart when the result is chartable. Built on
the [Chinook](https://github.com/lerocha/chinook-database) sample music store
dataset.

> "Which five artists generated the most sales?" → a one-sentence answer, a
> bar chart, the result table, and the generated SQL.

## Screenshot

![App demo](docs/screenshots/app-demo.png)

## Stack

- **Backend:** FastAPI + OpenAI (structured output) + PostgreSQL (psycopg3)
- **Frontend:** Vue 3 + Vite + Chart.js
- **SQL safety:** [`sqlglot`](https://github.com/tobymao/sqlglot)-based validation, a read-only DB user, read-only transactions, statement timeouts, row limits
- **Packaging:** Docker Compose (local Postgres), Render (deploy)

## Run it locally

```bash
docker compose up -d
cd backend
uv run uvicorn backend.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm run dev
```

Then open:

- **Frontend:** <http://localhost:5173>
- **Backend docs:** <http://localhost:8000/docs>

First time setup (dependency install, `.env` files) is covered in
[`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md).

## Deployment

The included [`render.yaml`](render.yaml) is a [Render Blueprint](https://render.com/docs/blueprint-spec)
that provisions all three pieces in one go: a managed Postgres database, the
FastAPI backend as a web service, and the Vue app as a static site.

1. Push this repo to GitHub.
2. In Render: **New > Blueprint**, point it at the repo.
3. Render reads `render.yaml` and creates the database + both services.
4. Set the `OPENAI_API_KEY` secret on the backend service when prompted (it's
   intentionally left out of `render.yaml`).
5. Seed the database using `database/seed.sql` (not `chinook.sql` — that
   file starts with `DROP DATABASE / CREATE DATABASE / \c chinook` which
   Render's managed Postgres user cannot run):
   ```bash
   psql "$DATABASE_URL" -f database/seed.sql
   psql "$DATABASE_URL" -f database/init/zz-read-only-sql-user.sql
   ```
6. After seeding, override the backend's `DATABASE_URL` in Render's
   environment tab to use `readonly_user` instead of the default `app` user
   that Render wires in automatically. The app connects as `readonly_user`;
   Render's auto-generated connection string uses `app`.
7. Once both services are live, update the live demo link at the top of this
   README.

Render, Railway, and Fly.io are all reasonable choices here; Render was
picked because one Blueprint file can describe the database, backend, and
frontend together instead of three separate dashboards.

## How it works

1. The backend fetches the live database schema and sends it, plus the
   question, to the LLM with a structured-output schema (`{"sql": "..."}`).
2. The returned SQL is validated, executed against a read-only Postgres
   connection, and the resulting rows are fed back to the LLM to produce a
   plain-English answer.
3. The frontend renders the answer, a bar chart (when the result is exactly
   one category column + one numeric column), the result table, and the
   generated SQL in a collapsed `<details>`.

See [`backend/src/backend/pipeline.py`](backend/src/backend/pipeline.py) for
the full request flow.

## Safety guardrails

The model's SQL is untrusted input. Before anything touches the database,
[`sql_validator.py`](backend/src/backend/sql_validator.py) parses it with
`sqlglot` and rejects it unless:

- it is exactly one statement, and that statement is a `SELECT`,
- no write expression (`INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`CREATE`/...)
  appears anywhere in the tree — including hidden inside a CTE,
- it doesn't use `SELECT INTO`, row-locking clauses, or a handful of
  resource-affecting Postgres functions (`pg_sleep`, `pg_read_file`, ...).

The validator then rewrites the query with a hard `LIMIT 100` if one isn't
already present (or lowers an oversized one). On top of that, the database
connection itself runs in `SET TRANSACTION READ ONLY` with a 5-second
statement timeout, against a Postgres role that only has read grants — so
even a bug in the validator can't turn into a write.

## Self-correction loop

When the validated SQL fails to *execute* (wrong table/column name, type
mismatch, etc.), the backend gets exactly one shot at fixing it: the failed
SQL and the raw database error are sent back to the model through a
dedicated `fix_sql` prompt, and the corrected query is validated and run
again from scratch. If that also fails, the error is raised rather than
retried again — no unbounded loop.

Validation failures are handled differently and are *never* retried: if the
SQL is unsafe, that's a bug in generation, not something worth asking the
model to "fix" with another guess.

The `/ask` response includes `attempts` and `corrected` so you can see when
this kicked in.

## Evals

[`evals/questions.json`](evals/questions.json) has 10 real questions across
easy/medium/hard difficulty, each with an expected result. Run them with:

```bash
cd backend
uv run python -m backend.eval_runner
```

Latest run: **10/10 passed** against `gpt-4.1-mini`. Since the model's output
isn't deterministic, treat this as a snapshot rather than a guarantee — rerun
it after prompt changes.

## Limitations

- Single-table-question style works well; deeply ambiguous or multi-step
  questions ("compare this quarter to last, excluding refunds") aren't tested.
- No conversation memory — every question is independent, so follow-ups like
  "now break that down by month" don't have context from the previous answer.
- The chart logic is a simple frontend heuristic (exactly 2 columns, second
  one numeric) rather than something the model decides, so a chartable
  3-column result won't get a chart.
- One dataset (Chinook). Nothing here is general-purpose "talk to any
  database."

## What I'd improve next

- Tool calling instead of structured-output string parsing for SQL
  generation — the more standard way real agentic systems call out to tools.
- Schema retrieval (RAG) so a much larger schema doesn't have to be sent in
  full on every request.
- Let the model choose the chart type instead of a fixed frontend rule.
- A second eval pass that checks the *prose* answer's correctness, not just
  the underlying rows.
