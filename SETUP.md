# Options Research & Evaluation Agent: Start Here

Read this file first, then PRD.md, then CLAUDE.md, then BUILD_STAGES.md. Four files total. Drop all four into the root of a new repo before your first Claude Code session.

## What you are building, in one paragraph

A scheduled system that watches five tickers, pulls live option chains and news, asks an LLM to form a directional hypothesis (long call, long put, or no trade), validates that hypothesis against hard liquidity and risk rules in code, opens a simulated position with conservative fill assumptions, and days later scores the result against real prices. Three cohorts run side by side: hold cash, a rule-based screener, and the LLM agent. A React dashboard shows everything. The agent is structurally unable to place a real order because it never has access to any brokerage execution function.

## What you will actually be doing this week

Roughly 15 hours across three roles:

1. Operator (about 8 hours). Running Claude Code loops from BUILD_STAGES.md, reading what it produced, reviewing diffs, deciding whether a stage is done. This is not passive. Read every test it writes.
2. Author and reviewer (about 5 hours). Writing the Dockerfiles yourself (Stage 0b). Designing the dashboard in Claude Design, then reviewing every TypeScript file Claude Code builds in Stage 8, making at least one change by hand per view, and asking it to explain anything you cannot.
3. Reviewer (about 2 hours). Reading the agent's first real research outputs and its logs on Friday and Saturday. This is where you start learning options.

## Before Wednesday: four things to confirm

1. Whether your $100 of Fable credits work through Claude Code, the Anthropic API, or both. Everything below assumes Claude Code.
2. You have a separate Anthropic API key for the runtime agent. The agent itself runs on claude-sonnet-5, not Fable. That is paid separately and keeps running after Saturday. Budget: a daily run on 5 tickers is well under a dollar a day.
3. Docker Desktop and Node 20+ are installed and working locally.
4. Postgres is not installed locally. It runs in Docker Compose only. Do not install it natively, it causes port conflicts.

## Stage 0 spike: the one thing that can change the plan

Before any real code, spend 30 minutes finding out whether a headless Python MCP client can authenticate to Robinhood's Trading MCP and call one read tool (get_equity_quotes). Robinhood's connector is designed for agent platforms like Claude Desktop and Claude Code; whether it accepts a standalone client with a long-lived session is unconfirmed.

Two outcomes, both fine:

- It works: the DataGateway's first adapter is RobinhoodAdapter. Store the token in an env var loaded only by the gateway container.
- It does not work, or OAuth requires a browser every session: the first adapter is YFinanceAdapter. yfinance gives option chains with bid, ask, volume, open interest, and implied volatility for free with no auth. The Robinhood adapter becomes a Phase 3 task.

Either way the rest of the build is identical, because the agent only ever sees the gateway's typed functions, never the data source.

Do not spend more than 30 minutes on this. If you are still fighting OAuth at minute 31, use yfinance and move on.

## Setting up the repo

```
mkdir options-research-agent && cd options-research-agent
git init
# copy PRD.md, CLAUDE.md, BUILD_STAGES.md, SETUP.md here
git add . && git commit -m "Planning docs"
claude
```

Your first message to Claude Code is the kickoff prompt at the top of BUILD_STAGES.md. Nothing else. It reads the planning docs, then starts Stage 0.

## How the loops work

Each stage in BUILD_STAGES.md has:

- Goal: what exists when it is done
- Done when: a checkable list. Every item is a test that passes, a command that succeeds, or a file that exists. Nothing subjective.
- Prompt: what you paste to start the stage
- Your job: what you review before marking it done

Claude Code marks a stage DONE in BUILD_STAGES.md only after every "Done when" item is verified by actually running it. If it cannot finish, it writes BLOCKED.md with what it tried and stops. That is your signal to step in.

Model per stage: BUILD_STAGES.md has a table at the top mapping each stage to Sonnet 5 or Fable 5.1. Stages 1 through 7 alternate models almost every step, so they're sent one at a time with the single-stage prompt, switching `/model` right before Stages 2, 4, and 6. Stage 8 is the one stretch that runs on a single model (Sonnet 5) throughout, so that's the one you can hand off as a short chained loop, stopping after each view for your review.

## Suggested schedule

| Day | What | Hours |
|---|---|---|
| Tue night | Read all four files. Confirm credits and API key. Confirm Fable is reachable from Claude Code. Install Docker/Node. | 1 |
| Wed | Stage 0 spike (30 min), then Stage 0b scaffold with Claude Code. Write Dockerfiles yourself. Send Stages 1 through 4 one at a time, switching model before 2 and 4. | 3 |
| Thu | Send Stages 5 through 7 one at a time, switching model before 6. Fix anything blocked. | 3 |
| Thu night | Design in Claude Design, export to docs/design/, run Stage 8a and the Today view. | 2 |
| Fri | Remaining three views with review after each. Stage 9 CI hardening. First real scheduled run. Read the agent's output. | 3 |
| Sat | Second real run. Fix what the first run exposed. Use remaining credits on code review, README, and the resume writeup draft. | 3 |

## What "finished" means for Saturday

The vertical slice runs end to end on real data: snapshot, screener, agent, validation, paper position, dashboard. CI is green. The evaluator is tested on fixtures but has no real results yet, because positions need days to mature. That is expected. Real scores arrive the following week with no credits needed.

## After Saturday, no credits needed

1. Let it run daily for three to four weeks. Read the agent's reasoning every day. This is your options education.
2. Deploy to a small VPS so it runs with your laptop closed. Docker Compose makes this a copy-and-run job.
3. Phase 3 only after you have weeks of scored results and you have read them: open and fund a Robinhood Agentic account with money you can lose entirely, add the ExecutionGateway with per-trade approval, and keep the hard limits in code.

## What goes on the resume, and when

Only after it is true and you can defend it. Not on Saturday. A draft for when the evaluator has real results:

Options Research & Evaluation Agent | Python, FastAPI, Postgres, Docker, React/TypeScript, GitHub Actions
- Built a scheduled LLM research agent that forms structured long-call, long-put, or no-trade hypotheses from live option chains and news, validated by deterministic liquidity and risk rules before entering a simulated portfolio.
- Isolated the agent behind a read-only data gateway with a hardcoded tool allowlist and a CI test that fails if any order-placement capability reaches the agent, so the research system cannot execute trades.
- Evaluated every hypothesis prospectively against realized prices across three cohorts (cash, rule-based screener, LLM), with per-cohort metrics served to a React dashboard.

Per your own rules: Docker, FastAPI, Postgres, and CI go into the Skills lines once you have written and debugged them yourself, which this plan is designed to make true.
