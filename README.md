# Paperhands

A personal, full-stack agentic research system that tests one question prospectively, on market data it has never seen:

> Does an LLM research agent add measurable value over a deterministic rule-based options screener, and over holding cash?

Every trading day it pulls live quotes, option chains, an earnings date, and headlines for five tickers; asks three independent strategies for a decision on each; validates every decision against hard rules in code; opens simulated positions at conservative fills; and, days later, scores each one against realized prices. A FastAPI back end and a React dashboard show everything.

It is an experiment and a learning tool. It is not expected to be profitable, and a negative result is a valid outcome. It never places a real order, and it is built so that it cannot.

## The three cohorts

All three see the same data on the same day and each produces one decision per ticker. A is the benchmark, B is the control, C is the hypothesis under test.

| Cohort | Who decides | How |
| --- | --- | --- |
| **A - Cash** | Nobody | Records `no_trade` every run. Zero return, by definition. |
| **B - Screener** | Deterministic code | 20-day return and RSI(14) thresholds choose `long_call`, `long_put`, or `no_trade`; then picks the eligible contract nearest a target DTE and the money. Rules in `src/screener/`. |
| **C - Agent** | `claude-sonnet-5` | Receives a context bundle (quote, the same two indicators, earnings date, headlines, and the list of already-eligible contracts) and returns one structured `TradeCandidate`: an action, a contract id, a thesis, evidence for, evidence against, a 0-1 confidence, and an invalidation condition. |

The rule the whole codebase is built around: **the LLM handles semantic uncertainty; deterministic code handles every invariant.** The agent may argue a direction. It never computes P&L, max loss, or liquidity; never chooses a contract that code has not already marked eligible; and any output containing a number other than its own confidence is rejected and logged. Quantity, fills, max loss, marks, P&L, and scoring live in `src/validator/`, `src/portfolio/`, and `src/evaluator/` - never in `src/agent/`.

## The capability boundary

The Robinhood Trading MCP connector this system authenticates against has full trading scope: the OAuth token it holds could place, review, cancel, and exercise real option orders. The architecture makes those unreachable rather than merely unused.

1. **A hardcoded allowlist.** `src/gateway/allowlist.py` names the only five functions the agent may ever call: `get_quote`, `get_option_chain`, `get_historicals`, `get_earnings_date`, `get_news`. It is a tuple in source, read from no config file and no environment variable.
2. **A gateway with no generic dispatch.** `DataGateway` exposes exactly those five as named methods, each tagged `is_mutating = False`. The agent is handed the bound methods, never the gateway object or the adapter. Any other attribute lookup raises `CapabilityError`.
3. **A second, independent allowlist at the transport.** `src/gateway/adapters/mcp_client.py` keeps its own frozen set of seven read-only MCP tool names and raises `CapabilityError` for anything else before a request is built. The agent-facing layer and the transport layer would both have to be compromised for a write to reach the broker.
4. **A CI job that fails if the boundary moves.** `tests/test_capability_boundary.py` runs as its own named check on every commit. It asserts the agent's tool list is exactly the five functions and nothing is mutating; scans every source and doc file under `src/agent/` plus the allowlist for order-placement strings; and asserts no environment variable declared for the worker contains `EXEC`, `TRADING`, or `AGENTIC`. It is the one file in the repository allowed to spell those strings out.
5. **One credential, one reader.** The OAuth token lives in a gitignored file whose path only the adapter reads. The API process never touches the gateway at all - it only reads back what the worker already computed and stored.

Redaction runs before logging: anything matching an account-number pattern is replaced with `[REDACTED]` before it reaches Postgres or stdout.

## Pipeline

```
Watchlist (5 tickers)
   |
Snapshot job ............ quotes, option chain, earnings date, headlines -> Postgres
   |
Eligibility filter ...... DTE window, max spread %, min open interest, max premium
   |                       (deterministic; every contract marked eligible or not, with a reason)
   +--> Cohort A: cash
   +--> Cohort B: screener
   +--> Cohort C: agent
   |
Validator ............... rejects any candidate whose contract is not eligible, whose
   |                       action and contract type disagree, or whose max loss exceeds the cap
   |
Paper portfolio ......... open at ask, one contract, max_loss = ask x 100
   |
Daily mark / close ...... mark at bid; close after 5 trading days or 2 trading days
   |                       before expiry, whichever first; zero if the bid is missing
   |
Evaluator ............... realized P&L, direction correctness, per-cohort aggregates
   |
FastAPI -> React dashboard
```

Thresholds and the watchlist are in `src/config.py` (currently DTE 28-45, spread at most 5% of mid, open interest at least 500, premium at most $300 - tuned from the PRD defaults in Stage 4; see `NOTES.md`). The trading-day calendar is a hardcoded NYSE holiday list in the same file.

## Running locally

Prerequisites: Python 3.12, Node 22, Docker Desktop. Postgres runs in Docker only - do not install it natively.

```sh
cp .env.example .env            # set ANTHROPIC_API_KEY; ADAPTER=fake needs no broker token
docker compose up -d postgres
make install                    # pip install -e ".[dev]"
alembic upgrade head

make robinhood-auth             # ADAPTER=robinhood only: one-time browser consent,
                                # writes data/robinhood_token.json (gitignored)

make run-daily                  # one full run: snapshot, eligibility, three cohorts,
                                # validation, fills. Real API calls if ADAPTER=robinhood.
make run-mark                   # mark open positions, close any at horizon, evaluate

docker compose up -d            # api on :8000, worker on the schedule below,
                                # frontend container on :3000

cd frontend && npm install && npm run dev    # dashboard on :5173 during development
```

The worker runs the daily job at 10:30 ET and the mark/close job at 16:15 ET, on trading days only. The API is read-only; its endpoints are `/runs/latest`, `/decisions`, `/positions`, `/metrics`, and `/logs`. The frontend container builds the dashboard in a Node stage and serves the static output from nginx, with a fallback to `index.html` so the app's own routes survive a refresh.

`make check` runs everything CI runs: `ruff`, `mypy --strict`, and `pytest`. The integration tests need the compose Postgres up and skip cleanly if it is not; the one live-broker test is opt-in with `ROBINHOOD_LIVE_TESTS=1`.

## CI

Six jobs on every push and pull request: `ruff + mypy --strict`, `pytest unit`, `pytest integration (Postgres)` against a real Postgres service (and configured to fail rather than skip if that service is missing), `capability boundary` as its own check, `docker compose build` for all services, and `npm run build` for the dashboard.

## Results

**Pending.** Positions need five trading days to mature and the evaluator scores only closed positions. This section will be filled in after four weeks of daily runs, with per-cohort hit rate, mean and median P&L, total P&L, and max drawdown as the evaluator produces them, and a stated verdict on whether Cohort C beat Cohort B.

Whatever appears here will be simulated, conservative-fill results and will be labelled as such. No number will be added that the evaluator did not produce.

## Reading further

- `PRD.md` - the specification: purpose, scope, the non-goals, the honesty rules.
- `CLAUDE.md` - the engineering rules the build was held to.
- `BUILD_STAGES.md` - the stage-by-stage plan and what "done" meant for each.
- `NOTES.md` - every design decision, deviation, and bug, with the reasoning.
