# CLAUDE.md

You are building the Options Research & Evaluation Agent described in PRD.md, one stage at a time, following BUILD_STAGES.md. Read both files fully before doing anything.

## Non-negotiable rules

1. Scope is PRD.md section 4. If a task is in section 5 (out of scope), do not build it, even if it seems easy or helpful. Note it in NOTES.md and move on.
2. Never write, import, reference, or stub any function that places, reviews, cancels, or exercises an order. Not in tests, not in comments, not as a TODO. The only exception is the deny-list strings inside tests/test_capability_boundary.py.
3. The agent (src/agent/) may only call the five DataGateway functions in PRD.md section 7. No generic tool dispatch. No direct imports of the adapter or any credential.
4. The agent never computes money. Quantity, max loss, P&L, fills, and scoring live in src/validator/ and src/portfolio/ and src/evaluator/, never in src/agent/.
5. Every number the system produces comes from code, never from the LLM. If the LLM returns a number other than confidence, reject the output.
6. Redact before logging. Anything matching an account number pattern or containing "account" plus digits is replaced with [REDACTED] before it reaches the database or stdout.
7. No secrets in code, tests, fixtures, or logs. All secrets come from .env, which is gitignored. .env.example lists every variable with a placeholder.
8. Do not write the Dockerfiles (Stage 0b). Jayden writes those; you review them when asked, and you may write docker-compose.yml. You build the frontend in Stage 8 one view at a time, stopping after each view so Jayden can review it.
9. Do not mark a stage DONE until every "Done when" item in BUILD_STAGES.md has been verified by running it. Paste the command output in your final message for the stage.
10. If blocked for more than three attempts on the same problem, write BLOCKED.md with what you tried and what you need, commit, and stop. Do not work around a blocker by relaxing a rule above.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, APScheduler, httpx, pytest, ruff, mypy
- Postgres 16 (Docker only)
- Anthropic Python SDK. Runtime model: claude-sonnet-5. Use structured output for TradeCandidate.
- React 18 + TypeScript (strict) + Vite, no UI or state library, styling from docs/design/STYLE_GUIDE.md
- Docker Compose services: api, worker, postgres, frontend
- GitHub Actions

Do not add other frameworks. Specifically not: LangChain, LlamaIndex, Celery, Redis, Prisma, an ORM other than SQLAlchemy, or any options pricing library.

## Repository layout

```
src/
  gateway/        DataGateway, adapters (robinhood.py or yfinance.py), allowlist.py
  models/         SQLAlchemy models
  screener/       Cohort B rule-based screener
  agent/          Cohort C: context bundle builder, prompt, TradeCandidate schema, runner
  validator/      eligibility filter and candidate validator
  portfolio/      paper positions, fills, marks, closes
  evaluator/      scoring and per-cohort metrics
  scheduler/      APScheduler jobs: daily_run, daily_mark
  api/            FastAPI app and read endpoints
  logging/        run logger and redaction
  config.py       settings from env, watchlist, thresholds
alembic/
tests/
  unit/
  integration/
  fixtures/       synthetic snapshots with known-answer evaluations
  test_capability_boundary.py
frontend/         built in Stage 8, reviewed by Jayden
docs/design/      Claude Design mockups and STYLE_GUIDE.md
docker-compose.yml
.github/workflows/ci.yml
.env.example
BUILD_STAGES.md   stage tracker; you edit the status lines
NOTES.md          decisions, deferred items, questions for Jayden
BLOCKED.md        only exists when you are stuck
```

## How to work

- Start every session by reading BUILD_STAGES.md and finding the first stage not marked DONE.
- Write tests before or alongside code. A stage with no new tests is not done.
- Run `make check` (ruff, mypy, pytest) before claiming anything works.
- Commit at the end of every stage with the message "Stage N: <goal>". One commit per stage.
- Keep files under 300 lines. Split when they grow.
- Type everything. mypy --strict on src/.
- When you make a design decision the PRD does not cover, write one line in NOTES.md saying what you chose and why.
- When something in the PRD looks wrong, do not silently change it. Write the question in NOTES.md and follow the PRD as written.

## Conventions

- Money is Decimal, never float. Store as NUMERIC(12,4).
- All timestamps UTC, timezone-aware.
- Trading day math uses a hardcoded NYSE holiday list for 2026 and 2027 in src/config.py. No external calendar library.
- Contract IDs are the adapter's native identifier (OCC symbol for yfinance, instrument UUID for Robinhood), stored as a string.
- Every database write in the daily run is inside one transaction per cohort, so a failed cohort does not lose the others.

## What good looks like at the end of a stage

Your final message for a stage contains: the list of files created or changed, the output of `make check`, the output of any command in the stage's "Done when" list, and the updated status line from BUILD_STAGES.md. Nothing else. No summaries of what you learned.
