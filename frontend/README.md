# Chat With Your Data — Frontend

A minimal Vue 3 + Vite single-page app: ask a question, see the plain-English
answer, the generated SQL, and the result rows.

## Requirements

- Node.js 20.19+ or 22.12+

## Install dependencies

From the repository root:

```bash
cd frontend
npm install
```

## Start the backend first

The dev server proxies `/ask` and `/health` to the backend at
`http://127.0.0.1:8000` (see `vite.config.js`), so the backend needs to be
running before you ask a question.

From the repository root:

```bash
docker compose up -d
cd backend
uv run uvicorn backend.main:app --reload
```

See [`../backend/README.md`](../backend/README.md) for backend setup details.

## Run the development server

From the `frontend` directory:

```bash
npm run dev
```

Open <http://localhost:5173>. Requests to `/ask` are proxied to the backend
automatically — no separate configuration needed.

Stop the server with `Ctrl+C`.

## Build for production

```bash
npm run build
npm run preview
```

The production build does not proxy API requests. If the backend is deployed
at a different origin than the frontend, set `VITE_API_BASE_URL` (see
[`.env.example`](.env.example)) before building:

```bash
cp .env.example .env
# edit .env, then:
npm run build
```
