# BUILD_STAGES.md

Status values: TODO, IN PROGRESS, DONE, BLOCKED. Claude Code updates these. Jayden owns Stage 0a and the Dockerfiles in Stage 0b, and reviews every file in Stage 8.

## Model per stage — read this before sending anything

Stages alternate models, and Claude Code cannot switch its own model mid-session. Check `/model` before each stage below and switch if the row doesn't match what's currently selected.

| Stage | Model | Send as |
|---|---|---|
| 0a | — (you, no Claude Code) | manual |
| 0b | Sonnet 5 | kickoff prompt |
| 1 | Sonnet 5 | single-stage prompt |
| 2 | **Fable 5.1** | single-stage prompt |
| 3 | Sonnet 5 | single-stage prompt |
| 4 | **Fable 5.1** | single-stage prompt |
| 5 | Sonnet 5 | single-stage prompt |
| 6 | **Fable 5.1** | single-stage prompt |
| 7 | Sonnet 5 | single-stage prompt |
| 8a, 8b (all 4 views) | Sonnet 5 | chained loop prompt (one model throughout, so this one can batch) |
| 9 | **Fable 5.1** | single-stage prompt |
| Saturday wrap-up | **Fable 5.1** | single-stage prompt |

First, confirm Fable actually appears in `/model` inside Claude Code, or that `claude --model claude-fable-5-1` is accepted. If neither works, your credits may only apply in the claude.ai chat interface, not Claude Code — check your account before relying on this table, and if Fable isn't reachable from Claude Code, run everything on Sonnet 5 and skip the switches below.

Because stages 1 through 7 alternate models almost every step, there is no single unattended overnight run across that whole range. Send each stage as its own message, from the "## Stage N" section below, switching model right before stages 2, 4, and 6. You're reviewing every diff per CLAUDE.md rule 9 anyway, so sending one stage at a time costs you nothing.

## How to send a stage

Copy the exact text inside the code block under that stage's "## Stage N" heading below, and paste it as your message. That's it, that block is the prompt. Before pasting it, check `/model` against the table above and switch if needed.

The kickoff prompt below is the one exception, since it's what starts the whole session. After that, every stage's prompt lives under its own heading further down in this file.

## Kickoff prompt (paste as your first message in Claude Code, model: Sonnet 5)

Send this only after you've done Stage 0a yourself and written the ADAPTER line in NOTES.md.

```
Read SETUP.md, PRD.md, CLAUDE.md, and BUILD_STAGES.md in full. Stage 0a is already done — check NOTES.md for the ADAPTER decision. Start Stage 0b.

Loop rules for this session:
- Work on the first stage marked TODO or IN PROGRESS.
- A stage is DONE only when every item under its "Done when" list has been run and passed. Paste the output.
- Stage 0b ends with a question for me about the Dockerfiles — stop there and wait.
- If blocked three times on the same problem, write BLOCKED.md, commit, and stop.
Begin.
```

## Chained loop prompt (Stage 8 only — one model throughout, so this one can run several steps unattended)

```
Continue from BUILD_STAGES.md. Run Stage 8a, then Stage 8b for Today, then Positions, then Scoreboard, then Logs, in that order, using the prompts under "## Stage 8" in that file. Stop after Stage 8a and after each Stage 8b view and wait for me before continuing — I'm reviewing and making a change by hand between each one. If blocked three times on the same problem, write BLOCKED.md, commit, and stop.
```

## Resume prompt (any later session — use only if you're unsure where you left off)

```
Read BUILD_STAGES.md and NOTES.md. Check for BLOCKED.md. Tell me which stage is next and what model it needs per the table at the top of BUILD_STAGES.md. Do not start it — wait for me to confirm the model is switched and paste that stage's own prompt.
```

---

## Stage 0a: Data spike (Jayden, 30 minutes max, before Claude Code)

Status: DONE

Goal: Decide the Phase 1 data adapter.

Test: from a plain Python script, connect an MCP client to Robinhood's Trading MCP endpoint and call get_equity_quotes for one ticker.

Done when:
- One of these two lines is written at the top of NOTES.md: "ADAPTER=robinhood, headless auth confirmed, token lifetime: <what you observed>" or "ADAPTER=yfinance, Robinhood headless auth deferred to Phase 3, reason: <what failed>".

Prompt to give Claude Code if you want help with the spike (optional, keep it short):
```
Write a single-file Python script using the official mcp Python SDK that connects to a remote MCP server URL from an env var MCP_URL, lists available tools, and calls get_equity_quotes with symbol AAPL. Handle OAuth if the server requires it. Print the result. No other files.
```

## Stage 0b: Repo scaffold and Docker (Claude Code scaffolds; Jayden writes the Dockerfiles)

Status: DONE

Goal: An empty but running project. Four Compose services come up healthy. CI runs and passes on a trivial test.

Prompt:
```
Stage 0b. Create the repository layout from CLAUDE.md with placeholder modules, pyproject.toml with the listed dependencies, a Makefile with targets install, check (ruff + mypy + pytest), and run-daily, .env.example, .gitignore, a tests/unit/test_smoke.py, docker-compose.yml with services api, worker, postgres, frontend, and .github/workflows/ci.yml that runs make check with a Postgres service container. Leave Dockerfile.api, Dockerfile.worker, and frontend/Dockerfile as empty files with a comment "Jayden writes this"; do not write their contents. Configure the adapter named in NOTES.md as the default in config.py. Then stop and tell me what the Dockerfiles need to do so I can write them.
```

Your job: write the three Dockerfiles yourself. Claude Code tells you what each container needs (base image, install step, entrypoint) and you write them. Then ask it to review:
```
Review the three Dockerfiles I wrote. Point out mistakes and explain why each matters. Do not rewrite them.
```

Done when:
- `docker compose up -d` shows all four services healthy (frontend can be a placeholder static page).
- `make check` passes locally.
- CI is green on the first push.
- .env.example lists ANTHROPIC_API_KEY, DATABASE_URL, RUNTIME_MODEL=claude-sonnet-5, and the adapter's variables.

## Stage 1: Schema and models

Status: DONE

Goal: Postgres schema for the entire Phase 1 pipeline, with Alembic migrations.

Prompt:
```
Stage 1. Design and implement the SQLAlchemy models and Alembic migration for: watchlist_symbols; runs (one per daily execution, with status and timing); snapshots (per run per ticker: quote, earnings date, news headlines as JSONB); contract_snapshots (per snapshot per contract: contract_id, type, strike, expiry, bid, ask, volume, open_interest, implied_vol, eligible boolean, ineligible_reason); decisions (per run per cohort: action, contract_id nullable, thesis and evidence fields as JSONB, confidence, validator_status, rejection_reason); paper_positions (cohort, contract_id, opened_at, open_price, quantity=1, max_loss, status, closed_at, close_price, close_reason); marks (position, date, bid); evaluations (position, realized_pnl, direction_correct, horizon_days); run_logs (run, level, component, message, payload JSONB). Money as NUMERIC(12,4), timestamps timestamptz. Write unit tests that create every model and one integration test that applies migrations to the CI Postgres and inserts one row per table.
```

Done when:
- `alembic upgrade head` succeeds on a fresh database.
- `alembic downgrade base` then `upgrade head` succeeds (migration is reversible).
- Integration test inserts a row in every table and passes in CI.
- `make check` passes.

## Stage 2: DataGateway and adapter

Status: DONE

Goal: The five allowlisted read functions, one working adapter, and the snapshot job.

Prompt:
```
Stage 2. Implement src/gateway/: an Adapter protocol with the five methods from PRD section 7, the adapter named in NOTES.md, and DataGateway which exposes exactly those five functions and nothing else, with a hardcoded ALLOWLIST tuple in allowlist.py. Each gateway function has an is_mutating attribute set to False. Any attempt to call a name not in ALLOWLIST raises CapabilityError. The adapter's credentials are read from env only inside the adapter module. Implement the snapshot job in src/scheduler/snapshot.py that, for each watchlist ticker, stores a snapshot row and contract_snapshot rows for every contract in the DTE window. Write tests/test_capability_boundary.py implementing all four assertions from PRD section 7. Write unit tests with a FakeAdapter and one integration test that runs the snapshot job against the live adapter for one ticker (skipped in CI if the adapter needs network).
```

Done when:
- `pytest tests/test_capability_boundary.py -v` passes and prints all four assertions.
- `make run-snapshot` (add this Makefile target) stores contract_snapshot rows for all 5 tickers locally, and you can see them with `psql` or a quick select.
- `make check` passes.

Your job: open allowlist.py and the gateway file and read every line. You will be asked about this in interviews.

## Stage 3: Eligibility filter, validator, and Cohort B screener

Status: DONE

Goal: Everything deterministic that sits between data and a decision.

Prompt:
```
Stage 3. Implement src/validator/eligibility.py, which marks each contract_snapshot eligible or not using the thresholds in PRD section 4 (read from config), storing ineligible_reason. Implement src/validator/candidate.py, which takes a TradeCandidate and the run's eligible contract list and returns Accepted or Rejected(reason): reject if the schema is invalid, the ticker is off-watchlist, the contract_id is not eligible for that ticker, the action and contract type disagree (long_call must be a call), or max_loss (ask x 100) exceeds MAX_PREMIUM. Implement src/screener/ for Cohort B: a documented rule set using 20-day return and 14-day RSI computed in code from historicals, choosing long_call if both bullish, long_put if both bearish, otherwise no_trade; contract selection picks the eligible contract closest to 30 DTE and closest to at-the-money. Implement Cohort A as a trivial no_trade decision. Write unit tests with fixtures covering every rejection reason and every screener branch.
```

Done when:
- Every rejection reason in candidate.py has a passing test that triggers it.
- Every screener branch (call, put, no_trade, no eligible contracts) has a passing test.
- Running eligibility on yesterday's snapshot produces a mix of eligible and ineligible rows with reasons you can read.
- `make check` passes.

## Stage 4: Research agent (Cohort C)

Status: DONE

Goal: The LLM produces a valid TradeCandidate from a context bundle, or is rejected and logged.

Prompt:
```
Stage 4. Implement src/agent/: schema.py with the TradeCandidate Pydantic model exactly as in PRD section 6; bundle.py which builds a plain-text context bundle per ticker from the snapshot (quote, 20-day return and RSI already computed by code, earnings date, top 5 headlines, and the list of eligible contracts with id, type, strike, expiry, DTE, bid, ask, OI, IV) and never includes any P&L or past decisions; prompt.py with a system prompt that instructs the model to act as a research analyst, choose long_call, long_put, or no_trade, cite specific data points from the bundle, list evidence against, and return only the schema; runner.py which calls claude-sonnet-5 with structured output, retries once on schema failure, and on second failure records no_trade with validator_status=rejected and reason schema_invalid. Every prompt and response is written to run_logs through src/logging/ with redaction applied. Add a CLI `make run-agent TICKER=AAPL` that runs the agent on the latest stored snapshot and prints the candidate. Tests: unit tests with a mocked Anthropic client covering valid output, invalid output then valid on retry, invalid twice, and a redaction test proving an account-number-like string never reaches the log table.
```

Done when:
- `make run-agent TICKER=<one of your five>` prints a TradeCandidate or a logged rejection, using the real API key.
- The run_logs table contains the prompt and response for that run, and a grep for digits patterns that look like account numbers returns nothing.
- All four mocked test cases pass.
- `make check` passes.

Your job: read the system prompt in prompt.py and the bundle it produced. If the bundle is missing something you would want as a human analyst, add it to NOTES.md as a Phase 2 item. Do not expand the bundle now.

## Stage 5: Paper portfolio

Status: DONE

Goal: Simulated positions with conservative fills, marks, and closes.

Prompt:
```
Stage 5. Implement src/portfolio/: open_position(cohort, decision) which re-checks eligibility at fill time, opens one contract at the current ask, and stores max_loss = ask x 100; mark_positions(date) which stores the bid for every open position (zero if missing); close_positions(date) which closes any position that has reached HORIZON_DAYS trading days since open or is within 2 trading days of expiry, at the bid, with close_reason horizon or pre_expiry; and a trading-day calendar in config using the hardcoded NYSE holiday list. Money is Decimal. Tests: fixtures with known bid/ask sequences proving open price, mark values, close timing across a weekend and across a holiday, and the zero-bid case.
```

Done when:
- Tests prove: fill at ask, mark at bid, close at horizon, close 2 days before expiry, correct handling of a weekend and of a listed holiday, zero-bid mark.
- A position opened from a Stage 4 candidate appears in paper_positions with max_loss equal to ask x 100.
- `make check` passes.

## Stage 6: Evaluator

Status: DONE

Goal: Scoring per position and per cohort, tested on known-answer fixtures.

Prompt:
```
Stage 6. Implement src/evaluator/: on position close, write an evaluation row with realized_pnl = (close_price - open_price) x 100, direction_correct = underlying moved in the thesis direction between open and close, horizon_days. Implement cohort_metrics(cohort, start, end) returning decisions, no_trade_count, trades, hit_rate, mean_pnl, median_pnl, total_pnl, max_drawdown, and pnl_vs_cash (cash is always zero). Build tests/fixtures/known_answers.json: a synthetic month of snapshots and decisions for all three cohorts where every metric is hand-computed and written into the fixture, and a test that runs the full pipeline on the fixture and asserts every metric matches to the cent.
```

Done when:
- The known-answer test passes and the fixture file contains the hand-computed expected values (you should be able to check two of them with a calculator).
- cohort_metrics returns sensible zeros for a cohort with no trades.
- `make check` passes.

Your job: pick two numbers in the fixture and recompute them by hand. If you cannot, the fixture is too complex; ask Claude Code to simplify it.

## Stage 7: Scheduler and end-to-end daily run

Status: DONE

Goal: One command runs the whole pipeline for today. APScheduler runs it at 10:30 ET on trading days and the mark/close job at 16:15 ET.

Prompt:
```
Stage 7. Implement src/scheduler/daily_run.py: create a run row, snapshot all tickers, apply eligibility, run Cohorts A, B, and C, validate, open positions, and mark the run complete; each cohort inside its own transaction so one failure does not lose the others. Implement daily_mark.py: mark then close then evaluate. Wire both into APScheduler in the worker entrypoint with the times from config, trading days only. Add `make run-daily` and `make run-mark`. Implement the FastAPI read endpoints: GET /runs/latest, GET /decisions?date=, GET /positions?status=, GET /metrics?cohort=, GET /logs?run_id=. Add an integration test that runs daily_run with the FakeAdapter and a mocked LLM and asserts one decision per cohort and correct position creation.
```

Done when:
- `make run-daily` completes against real data and the real API key with no errors, and the dashboard endpoints return the results.
- `make run-mark` completes (positions opened today will simply be marked, not closed).
- The integration test passes in CI.
- `docker compose up` shows the worker logging the next scheduled run time.
- `make check` passes.

STOP HERE. Before Stage 8, Jayden adds the Claude Design exports to docs/design/, and confirms the model is set to Sonnet 5.

## Stage 8: Dashboard (Claude Code builds, Jayden reviews every file)

Status: IN PROGRESS

Goal: React + TypeScript + Vite app with four views reading from the five API endpoints, matching the design in docs/design/.

**Deviation from the original plan (see NOTES.md for the full note):** Jayden did not export four PNGs + a separate STYLE_GUIDE.md. What actually exists in docs/design/ is a single Claude Design canvas export, `Paperhands.dc.html`, containing all four views (Today, Positions, Scoreboard, Logs) plus a fifth "Style guide" reference page as tabs within one file, alongside `support.js` (the canvas runtime, not a design artifact) and `uploads/` (a pasted reference image). `docs/design/STYLE_GUIDE.md` was written by transcribing that canvas's own embedded `:root` tokens, type scale, and glass/chrome CSS comments directly - not re-derived by eye. The four views below are read directly from the canvas's four `sc-if` sections instead of from PNGs.

Before starting: N/A - the design file is already in docs/design/, committed.

Prompt 8a (foundation):
```
Stage 8a. Read docs/design/STYLE_GUIDE.md and docs/design/Paperhands.dc.html (the four dashboard views live in that single canvas file's Today/Positions/Scoreboard/Logs sc-if sections - there are no separate PNGs). Scaffold frontend/ with Vite, React 18, and TypeScript in strict mode. Create src/theme/tokens.css with the color, radius, blur, and type tokens from the style guide as CSS variables. Create typed API interfaces in src/api/types.ts that exactly match the response models in the backend's src/api/schemas.py, and a small typed fetch client in src/api/client.ts. No UI library, no state library, no CSS framework. Build the app shell only: top bar, navigation, and routing for the four views with empty placeholders. Then stop and list every file you created with one line on what it does.
```

Prompt 8b (one view per loop, repeat for Today, Positions, Scoreboard, Logs in that order):
```
Stage 8b, view: <NAME>. Read the <NAME> sc-if section of docs/design/Paperhands.dc.html for layout/structure and the Component class's renderVals() for exactly which pieces of state map to which rendered elements. Build this view against the live API using the tokens in tokens.css and the types in types.ts - the canvas's own sample data (TICKERS, POS_OPEN, LOGS, etc.) is placeholder only; map real fields from src/api/types.ts onto the same visual structure, and where a real field doesn't exist yet (noted per-view in NOTES.md), say so and pick the simplest reasonable substitute rather than inventing fake data. Split it into small components, each under 150 lines. Glass and chrome effects must follow the style guide spec exactly and must not reduce text contrast. Handle loading, empty, and error states. When done, run npm run build, fix all TypeScript errors, and stop. Do not start the next view.
```

Your job after each 8b loop (this is the part that makes the TypeScript real):
1. Read every new file before approving. For anything you cannot explain line by line, ask:
```
Explain <file> to me line by line, focusing on the TypeScript: what each type does, why it is typed that way, and what would break if I removed it. Do not change the file.
```
2. Make at least one change yourself per view, by hand, before moving on. Rename a prop, add a column, change a type, fix a layout detail. Then ask Claude Code to review your change without rewriting it.
3. Compare against the design:
```
Open docs/design/Paperhands.dc.html to the <NAME> tab and compare it to the running page at http://localhost:5173/<route>. List visual differences, most important first. Do not fix them yet.
```

Done when:
- All four views render real data from the running API.
- npm run build succeeds with zero TypeScript errors under strict mode.
- The frontend container serves the built app.
- Every view shows the "Simulated results, conservative fills" label where P&L appears.
- Jayden can explain types.ts, client.ts, and one full view component without notes.

## Stage 9: CI hardening and docs

Status: TODO

Prompt:
```
Stage 9. Update ci.yml to run, in order: ruff, mypy --strict on src, pytest unit, pytest integration with the Postgres service, tests/test_capability_boundary.py as its own named job that must pass, docker compose build for all services, and npm run build for the frontend. Write README.md covering: what the system is, the capability boundary, the three cohorts, how to run locally, and a "Results" section that says results are pending and will be filled in after four weeks. Review all code in src/gateway, src/validator, and src/portfolio for anything that violates CLAUDE.md rule 2 or 4 and report findings without changing code.
```

Done when:
- CI shows the capability boundary job as a separate green check.
- README exists and you have read it and agree with every sentence.
- The review reports no violations, or you have fixed the ones it found.

## Saturday wrap-up prompt (remaining credits, model: Fable 5.1)

```
Read the whole repository. Produce three things in NOTES.md: (1) a list of the ten questions an interviewer would most likely ask about this codebase, each with the file and line that answers it; (2) a list of every place where a Phase 3 ExecutionGateway would need to plug in, without writing any of it; (3) the five most likely bugs in the daily run based on reading the code, ranked. Do not change any code.
```

---

## Phase 2 (after Saturday, no credits)

- Run daily for four weeks. Read every Cohort C thesis.
- Deploy to a VPS with Docker Compose.
- Add Phase 2 items from NOTES.md only after the first two weeks of results.

## Phase 3 gate checklist (do not start before all are true)

- [ ] At least 20 closed positions per cohort in the evaluator
- [ ] Jayden has read every Cohort C thesis and can name the agent's typical failure pattern
- [ ] Scoreboard reviewed; decision written in NOTES.md on whether Cohort C beats Cohort B
- [ ] ExecutionGateway designed with per-trade approval, MAX_LOSS_PER_TRADE, DAILY_LOSS_CAP, and a kill switch, all tested before any credential exists
- [ ] Robinhood Agentic account opened and funded with an amount Jayden is willing to lose entirely
