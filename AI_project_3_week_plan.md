# Chat-With-Your-Data — 3-Week Build Plan

A natural-language analytics agent: a user asks a question in plain English, an LLM
writes SQL against a real database, the query runs, and the app returns the answer —
ideally with a chart. Built on your existing strengths (Python, FastAPI, SQL, Vue) with
the in-demand AI layer on top.

**Assumes ~full days now that you've got the time. Pace is a guide, not a contract —
shipping something working beats hitting every checkbox.**

---

## What you'll have at the end

A deployed, public web app where anyone can ask questions of a sample dataset and get
grounded answers; a clean GitHub repo with a strong README and demo; and a short
write-up of how it works and where it breaks. That last part is what interviewers
actually probe.

## Tech stack (keep it boring and standard)

- **Backend:** FastAPI (your strength)
- **Database:** PostgreSQL with a real sample dataset (Chinook, or a Kaggle e-commerce set)
- **LLM:** an API with tool/function calling — Anthropic's Claude (e.g. a Sonnet-tier
  model) or OpenAI. Use a mid-tier model; you don't need the most expensive one.
- **Frontend:** Vue (your strength). Keep it to one page.
- **Charts:** Chart.js or a Vue chart wrapper
- **Packaging/deploy:** Docker, then Render / Railway / Fly.io (free-ish tiers)

---

## Week 0 — Prep (half a day, before Week 1)

**Definition of done:** repo exists, Postgres runs locally with data in it, you can call
the LLM API from a script.

- Create the GitHub repo today, even empty. Commit from day one — the visible history is
  part of the point given your profile's been quiet.
- Spin up Postgres locally (Docker is easiest) and load a sample dataset.
- Get an API key, send one hello-world request to the LLM from a Python script.
- Write your **test set**: 8–10 real questions you want the app to answer, from easy
  ("how many orders last month?") to harder ("top 5 customers by spend, with their
  country"). This doubles as your spec and your eval set later.

---

## Week 1 — Working end-to-end MVP

**Goal: an ugly but complete loop you can demo by Friday.** Resist polishing anything.

- **Days 1–2 — The core loop (no UI).** One script: take a hardcoded question, send the
  DB schema + the question to the LLM, instruct it to return *only* SQL, run that SQL,
  print the rows. Get it answering 3–4 of your test questions.
- **Day 3 — Make the answer human.** Feed the returned rows back to the LLM and have it
  write a plain-English answer ("Your top customer was X with £4,200 in orders").
  Now it's question in → answer out.
- **Day 4 — Wrap it in FastAPI.** One endpoint: `POST /ask` taking `{question}` and
  returning `{answer, sql, rows}`. Test it with curl / the FastAPI docs UI.
- **Day 5 — Minimal Vue front-end.** An input box, a "Ask" button, and a results area
  that shows the answer, the generated SQL, and a table of rows. Wire it to `/ask`.

**End of Week 1 you have a full-stack app that works on the happy path.** Commit and
push. If you only got this far, you already have a portfolio piece.

**Concepts to learn this week:** structured prompting (getting clean SQL out), passing
schema as context, basic FastAPI request/response models.

**Pitfall:** don't try to handle every edge case yet. Broken queries are Week 2's job.

---

## Week 2 — Make it an agent, and make it robust

**Goal:** it recovers from its own mistakes and feels less like a toy. This is where the
real AI-engineering learning is.

- **Days 1–2 — Tool calling instead of string parsing.** Refactor so the LLM calls a
  defined `run_sql` *tool* rather than you scraping SQL out of free text. This is the
  single most important concept to learn — it's how real AI products work, and great
  interview material.
- **Day 3 — Self-correction loop.** When a query errors, catch it, send the error back to
  the model, and let it retry (cap retries so it can't loop forever). Watching it fix its
  own SQL is the moment the project gets genuinely impressive.
- **Day 4 — Safety + guardrails.** Enforce that generated queries are read-only (reject
  anything that isn't a SELECT; use a read-only DB user). Add a row limit. This shows you
  think about what happens when the model misbehaves — a mature signal.
- **Day 5 — Charts.** When a result is chartable (e.g. a category and a number), have the
  app render a bar/line chart instead of just a table. Decide chart-or-table either with
  a simple rule or by asking the model.

**End of Week 2:** it handles bad questions gracefully, can't damage the database, and
visualizes results. Commit often.

**Concepts to learn this week:** LLM tool/function calling, retry/feedback loops,
guarding model output, prompt iteration.

**Pitfall:** scope creep. No login, no multi-user, no "support any database." One dataset,
done well.

---

## Week 3 — Polish, deploy, present

**Goal:** a live link and a repo that makes someone want to talk to you.

- **Day 1 — Evals.** Write a small script that runs all 8–10 test questions and reports
  how many produced correct answers. Even a rough pass/fail is gold — almost no junior
  candidate measures their AI's accuracy, and it gives you a number to talk about.
- **Day 2 — Tidy the UI.** Loading states, error messages, a sensible layout. It doesn't
  need to be beautiful, just not broken-looking.
- **Day 3 — Dockerise + deploy.** Containerise the stack, push to Render/Railway/Fly. Get
  a public URL. Seed it with the sample data so anyone can try it immediately.
- **Day 4 — README (this matters as much as the code).** What it is, a demo GIF, how it
  works (a small architecture diagram), the stack, your eval results, and an honest
  "limitations / what I'd do next" section. Link the live demo at the top.
- **Day 5 — Hook it into your search.** Add the repo + live link to your GitHub profile
  and your CV, and replace the `[TO BUILD]` placeholder with the real details.

**Concepts to learn this week:** lightweight evals for LLM apps, deployment, technical
writing.

---

## Stretch goals (only after the core is shipped)

- **Schema retrieval (RAG):** for a bigger database, embed table/column descriptions in a
  vector store and retrieve only the relevant ones per question. This adds real RAG to the
  project and lets you legitimately list vector databases / embeddings as skills.
- **Conversation memory:** support follow-ups ("now break that down by month").
- **"Show your working":** let the user expand to see the SQL and the model's reasoning.

## What this earns you in interviews

You'll be able to speak first-hand about tool calling, grounding model output in real data,
handling the model being wrong, guarding against destructive actions, and measuring
accuracy — which is most of what "AI engineering" actually means day to day. Keep a running
notes file of decisions and trade-offs as you build; it basically writes your interview
answers for you.

## Resources

- Your LLM provider's docs on **tool / function calling** — read this first; it's central.
- FastAPI docs (you know these).
- The Chinook sample database (small, relational, good for demoing joins).
