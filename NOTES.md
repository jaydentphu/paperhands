# NOTES.md

Decisions, deferred items, and questions for Jayden.

## Stage 0a: Data spike

ADAPTER=robinhood, headless auth confirmed, token lifetime: access token expires_in observed at ~746823s and ~821409s (~8.6-9.5 days) across two runs; refresh_token is issued (has_refresh_token=True), so unattended renewal without a browser is possible once a refresh token is persisted.

Method: ran `spike_mcp_oauth_test.py` (official `mcp` Python SDK, `streamable_http_client` + `OAuthClientProvider`) as a plain script against `https://agent.robinhood.com/mcp/trading`, independent of any Claude Code/Desktop session. The OAuth authorization-code + PKCE flow completed via a localhost callback server and the default browser, `session.list_tools()` returned 73 tools, and `get_equity_quotes(["AAPL"])` returned live data.

Important safety implication for Stage 2 (src/gateway/):
- The OAuth token's scope is `internal`, not read-only. The 73 tools returned include every order-placing, reviewing, cancelling, and exercising function (`place_option_order`, `place_equity_order`, `cancel_option_order`, `exercise_option`, `review_option_order`, etc.). Robinhood does not offer a narrower read-only scope for this MCP server.
- This means the capability boundary (PRD section 7 / CLAUDE.md rule 3) has zero support from the credential itself. It must be enforced entirely by DataGateway's code: the adapter module must never expose a generic `call_tool(name, args)`, and DataGateway's ALLOWLIST must be the only path the agent ever touches. Rule 2 (no order-placing function ever written/imported/stubbed) is the only thing standing between this credential and a real trade.
- Token persistence design needed in Stage 2: the spike used in-memory-only token storage (nothing written to disk). The real adapter needs a durable token store (refresh_token + access_token) written only inside src/gateway/adapters/robinhood.py, loaded from an env var pointing at a file path or secret, never logged, never passed to src/agent/. This still needs to be designed - flagging as a Stage 2 task, not deciding the mechanism now.
- One-time interactive consent was required to mint the refresh token (a browser had to complete the OAuth redirect once). That happened on Jayden's desktop machine with an already-authenticated Robinhood browser session, so no manual click-through was visibly needed this run - but a fresh machine (e.g., a VPS in the Phase 2 deploy) would need a one-time interactive re-auth before it can run headlessly. This matches Robinhood's own documentation ("you can only open an agentic account and authenticate your agent on a desktop device").

Spike artifact: `spike_mcp_oauth_test.py` at repo root, kept for reference. Not part of the src/ layout; not imported by anything in Stage 2.

## Stage 0b: Repo scaffold

Docker Desktop and `make` (via `winget install GnuWin32.Make`) were installed after a reboot. `make` is not on PATH in Git Bash by default - it's at `C:\Program Files (x86)\GnuWin32\bin\make.exe`, invoked by full path until Jayden adds it to PATH himself. Jayden wrote all three Dockerfiles by hand (with a line-by-line walkthrough of what each instruction does). Review found one real issue: no `.dockerignore` existed, and `Dockerfile.api`/`Dockerfile.worker` build with `context: .` (repo root), so the entire build context - including a future local `.env` with a real API key - would be uploaded to the Docker daemon on every build even though only `pyproject.toml` and `src/` get copied into the image. Added `.dockerignore` (excludes `.git`, `.env`, caches, `node_modules`, `docs/`) to close that gap; this is a build-config file, not one of the three Dockerfiles Jayden owns.

`docker compose up -d --build` brings up all four services healthy (postgres, api, worker, frontend). `GET /health` on the api returns `{"status":"ok"}`; the frontend serves the placeholder page; the worker logs its placeholder line. `make check` (ruff, mypy --strict, pytest) passes. CI is green on GitHub (run 35071197139, "Planning docs" push, completed success).

- Watchlist tickers: AAPL, MSFT, NVDA, AMZN, GOOGL - liquid large caps with active weekly/monthly options chains, per PRD section 4's "liquid large caps only." No PRD-specified list, so picked for options liquidity (tight spreads, high OI at many strikes).
- DB driver: `psycopg[binary]` (psycopg3), not psycopg2 or asyncpg - modern, actively maintained, works with SQLAlchemy 2.x sync engine which is simpler to reason about for a once-a-day batch job than an async engine.
- Package layout: `src/` is a regular package (has `__init__.py`) importable as `src.gateway`, `src.agent`, etc., with the repo root on `pythonpath` via pyproject's `[tool.pytest.ini_options]` and mypy's `mypy_path = "."`. No separate install step needed for tests/mypy to resolve imports; `make install` still does an editable install for running the app for real.
- `src/logging/` does not shadow the stdlib `logging` module because Python 3 absolute imports mean `import logging` always resolves to stdlib; only `from src.logging import ...` reaches this package.
- Frontend placeholder: added `frontend/index.html` as a static placeholder page (referenced by docker-compose's frontend service) so "frontend can be a placeholder static page" (Stage 0b done-when) is satisfiable once Jayden's Dockerfile serves it. Real dashboard replaces this in Stage 8.
- docker-compose port mapping: api 8000:8000 (uvicorn default), frontend 3000:80 (assumes a static/nginx-style Dockerfile serving on container port 80), postgres 5432:5432 (exposed to host for local `psql`/debugging use in Stage 1-2), worker has no exposed ports (internal scheduler process only).
- CI installs and runs via `make check`/`make install` directly - GitHub's `ubuntu-latest` runners ship `make` natively, so this doesn't depend on Jayden's local Windows `make` install.
