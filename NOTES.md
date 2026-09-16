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
