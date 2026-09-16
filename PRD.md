# PRD: Options Research & Evaluation Agent

Version 1.0, 15 Sept 2026. Scope is locked for the Phase 1 build. Anything not listed under "In scope" is out of scope until Phase 1 ships.

## 1. Purpose

A personal, full-stack agentic research system that tests one question prospectively, on unseen market data:

Does an LLM research agent add measurable value over a deterministic rule-based options screener and over holding cash?

The system is an experiment and a learning tool. It is not expected to be profitable, and a negative result is a valid outcome. Profitability is never a success criterion.

## 2. Core architecture principle

LLM handles semantic uncertainty: reading news, earnings context, technical state, and forming a directional thesis with evidence against it.

Deterministic code handles every invariant: contract eligibility, liquidity thresholds, position sizing, fill simulation, P&L, scoring, and authorization.

The agent never computes P&L, Greeks, max loss, or liquidity metrics. It never selects a contract that code has not already marked eligible. It never has access to any execution capability.

## 3. Pipeline

```
Watchlist (5 tickers)
   |
Snapshot job: quotes, option chain, earnings date, news headlines
   |  stored in Postgres with full bid/ask/OI/volume/IV per contract
   |
Eligibility filter (deterministic): DTE window, max spread %, min OI, max premium
   |  produces list of eligible contracts per ticker
   |
   +--> Cohort A: cash. Records no_trade every run.
   +--> Cohort B: rule-based screener. Deterministic rules pick long_call / long_put / no_trade.
   +--> Cohort C: LLM research agent. Receives context bundle + eligible contracts, returns TradeCandidate.
   |
Validator (deterministic): rejects any candidate whose contract is not in the eligible list,
   whose max loss exceeds the cap, or whose schema is invalid. Rejections are logged.
   |
Paper portfolio: opens position at ask, one contract, per cohort.
   |
Daily mark job: marks open positions at bid. Closes at horizon (H trading days) or 2 trading days before expiry, whichever first.
   |
Evaluator: on close, records realized P&L, direction correctness, and per-cohort aggregates.
   |
FastAPI -> React/TypeScript dashboard
```

## 4. In scope (Phase 1)

- Watchlist of 5 tickers, configured in one file. Liquid large caps only.
- One scheduled run per trading day, after market open (default 10:30 ET).
- Data gateway with an adapter interface and one live adapter (Robinhood MCP if Stage 0 spike succeeds, otherwise yfinance).
- Eligibility rules, all configurable with defaults:
  - DTE between 14 and 45
  - Bid/ask spread no more than 10% of mid
  - Open interest at least 500
  - Premium (ask x 100) no more than $300
  - Underlying must be on the watchlist
- Cohort B screener: a simple, documented rule set (for example: 20-day return and RSI thresholds choose direction; otherwise no_trade). The exact rule matters less than that it is deterministic and documented.
- Cohort C agent on claude-sonnet-5 with structured output, returning a TradeCandidate.
- Paper portfolio: long calls and long puts only. One contract per position. Buy at ask, mark and close at bid. If bid is zero or missing, mark at zero. No partial fills. Position rejected if contract fails eligibility at fill time.
- Horizon H = 5 trading days, configurable.
- Evaluator metrics per cohort: number of decisions, number of no_trade, hit rate on direction, mean and median realized P&L per trade, total P&L, max drawdown, versus cash.
- Full run logging: every prompt, response, tool call, validation decision, and rejection, with redaction of account identifiers.
- FastAPI read endpoints for the dashboard.
- React/TypeScript dashboard with four views: Today, Open Positions, Scoreboard, Run Logs.
- Docker Compose: api, worker, postgres, frontend.
- GitHub Actions: lint, type check, unit tests, integration test against a Postgres service, capability boundary test, Docker build.

## 5. Out of scope (Phase 1)

Short options, spreads, multi-leg, assignment, early exercise, Greeks modeling, partial fills, slippage models beyond bid/ask, authentication on the dashboard, SEC filing RAG, more than 5 tickers, intraday runs, any order placement, any Robinhood Agentic account, any real money, cloud deployment, cost tracking, prompt A/B testing.

## 6. TradeCandidate schema

The agent's only output. Enforced with Pydantic. Any output that fails validation is rejected and logged, and that run records no_trade for Cohort C.

```
TradeCandidate
  ticker: str                      # must be on watchlist
  action: "long_call" | "long_put" | "no_trade"
  contract_id: str | None          # must be in the eligible list for this run; None iff no_trade
  thesis: str                      # 2 to 5 sentences, the directional argument
  evidence_for: list[str]          # 2 to 4 items, each citing a specific data point from the bundle
  evidence_against: list[str]      # 2 to 4 items, what would make this wrong
  confidence: float                # 0.0 to 1.0
  invalidation: str                # one sentence, the observable that would close the idea early
```

The agent never provides quantity, price, max loss, or stop levels. Code sets quantity to 1 and computes max loss as ask x 100.

## 7. Capability boundary (the safety design)

The agent runs in the worker process. It receives a context bundle assembled by code and a list of tools that contains exactly the following read functions, exposed by the DataGateway:

```
get_quote(ticker)
get_option_chain(ticker, min_dte, max_dte)
get_historicals(ticker, days)
get_earnings_date(ticker)
get_news(ticker, limit)
```

There is no generic call_tool(name, args). The gateway has a hardcoded allowlist and raises on anything else. The Robinhood credential (if used) is loaded only inside the gateway module and is never passed to the agent, the API, or the frontend.

CI runs tests/test_capability_boundary.py, which asserts:

- The agent's tool list contains only the five functions above.
- No tool in the list has is_mutating = True.
- The strings "place_option_order", "place_equity_order", "review_option_order", "cancel", and "exercise" do not appear anywhere in src/agent/ or src/gateway/allowlist.py.
- The worker container's environment does not contain any variable with EXEC, TRADING, or AGENTIC in its name.

No Robinhood Agentic account exists during Phase 1. Nothing is opened or funded until Phase 3.

## 8. Phases

| Phase | Agent capability | Gate to enter |
|---|---|---|
| 1 | Read-only research, paper portfolio, evaluation | This build |
| 2 | Same, running unattended for 4+ weeks with real scored results | Phase 1 vertical slice green |
| 3 | Human-approved real orders in a funded Agentic account, small balance | 4+ weeks of Phase 2 results reviewed by Jayden; ExecutionGateway built with per-trade approval; hard limits in code |
| 4 | Bounded autonomy inside code-enforced limits | Phase 3 track record reviewed; kill switch and daily loss cap tested |

## 9. Non-goals and honesty rules

- Never present paper results as if they were real fills. The dashboard labels every number "simulated, conservative fills."
- Never let the agent see its own past P&L in its context bundle in Phase 1. It should not learn to chase.
- Never add a metric to the resume that the evaluator has not produced.

## 10. Success criteria for Phase 1

- docker compose up brings up all four services healthy.
- A manual trigger of the daily run stores a snapshot, three cohort decisions, and at least one paper position (or three no_trades) for the current day.
- Evaluator produces correct metrics on a fixture dataset with known answers.
- Capability boundary test passes in CI.
- Dashboard renders all four views from live API data.
- Jayden can explain every file in src/gateway/, src/validator/, and src/portfolio/ without notes.
