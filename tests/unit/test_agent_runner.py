"""Mocked-client tests for the four required cases: valid output, invalid
then valid on retry, invalid twice, plus a tool-call round and a refused
tool name."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pytest
from anthropic.types import Message

from src.agent.runner import SCHEMA_INVALID, AgentRunner
from src.gateway import ALLOWLIST, DataGateway
from src.gateway.adapters.fake import FakeAdapter
from src.logging import MemoryLogger
from src.models.enums import Action, LogLevel

TODAY = dt.date(2026, 9, 16)
BUNDLE = "TICKER: AAPL\nELIGIBLE CONTRACTS (1)\n  abc-1 | call | ..."


def _valid_json(**overrides: Any) -> str:
    data: dict[str, Any] = {
        "ticker": "AAPL",
        "action": "long_call",
        "contract_id": "abc-1",
        "thesis": "Momentum is strong and RSI confirms it.",
        "evidence_for": ["20-day return +4.12%", "RSI(14) 62.3"],
        "evidence_against": ["earnings in 43 days", "IV 0.251 is elevated"],
        "confidence": 0.62,
        "invalidation": "A close below the 20-day low.",
    }
    data.update(overrides)
    return json.dumps(data)


def _message(content: list[dict[str, Any]], stop_reason: str = "end_turn") -> Message:
    return Message.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-5",
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    )


def _text(text: str) -> Message:
    return _message([{"type": "text", "text": text}])


class FakeMessages:
    def __init__(self, responses: list[Message]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Message:
        # Snapshot the conversation: the runner keeps mutating the same list.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        if not self._responses:
            raise AssertionError("no more scripted responses")
        return self._responses.pop(0)


def _runner(responses: list[Message]) -> tuple[AgentRunner, FakeMessages, MemoryLogger]:
    messages = FakeMessages(responses)
    logger = MemoryLogger()
    runner = AgentRunner(messages, DataGateway(FakeAdapter(today=lambda: TODAY)), logger)
    return runner, messages, logger


def test_valid_output_is_returned_first_try() -> None:
    runner, messages, logger = _runner([_text(_valid_json())])
    outcome = runner.run("AAPL", BUNDLE)

    assert outcome.candidate is not None
    assert outcome.candidate.action == Action.LONG_CALL
    assert outcome.candidate.contract_id == "abc-1"
    assert outcome.attempts == 1
    assert outcome.rejection_reason is None

    call = messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert [t["name"] for t in call["tools"]] == list(ALLOWLIST)
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["messages"][0]["content"].startswith("Context bundle:")

    messages_logged = [e.message for e in logger.entries]
    assert any(m.startswith("prompt for AAPL") for m in messages_logged)
    assert any(m.startswith("response for AAPL") for m in messages_logged)


def test_invalid_then_valid_on_retry() -> None:
    bad = _valid_json(confidence=1.7)
    runner, messages, logger = _runner([_text(bad), _text(_valid_json())])
    outcome = runner.run("AAPL", BUNDLE)

    assert outcome.candidate is not None
    assert outcome.attempts == 2
    retry_prompt = messages.calls[1]["messages"][-1]["content"]
    assert "did not satisfy the required schema" in retry_prompt
    assert "confidence" in retry_prompt
    assert any(e.level == LogLevel.WARNING for e in logger.entries)


def test_invalid_twice_is_rejected_as_schema_invalid() -> None:
    runner, messages, logger = _runner(
        [_text("not json at all"), _text(_valid_json(action="no_trade"))]
    )
    outcome = runner.run("AAPL", BUNDLE)

    assert outcome.candidate is None
    assert outcome.rejection_reason == SCHEMA_INVALID
    assert outcome.attempts == 2
    assert len(messages.calls) == 2
    assert any(e.level == LogLevel.ERROR for e in logger.entries)


def test_wrong_ticker_counts_as_schema_failure() -> None:
    runner, _, _ = _runner([_text(_valid_json(ticker="MSFT")), _text(_valid_json())])
    outcome = runner.run("AAPL", BUNDLE)
    assert outcome.candidate is not None
    assert outcome.attempts == 2


def test_tool_call_round_is_dispatched_then_answer_parsed() -> None:
    tool_turn = _message(
        [{"type": "tool_use", "id": "toolu_1", "name": "get_quote", "input": {"ticker": "AAPL"}}],
        stop_reason="tool_use",
    )
    runner, messages, logger = _runner([tool_turn, _text(_valid_json())])
    outcome = runner.run("AAPL", BUNDLE)

    assert outcome.candidate is not None
    assert outcome.attempts == 1
    second_call = messages.calls[1]["messages"]
    tool_result = second_call[-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_1"
    assert json.loads(tool_result["content"])["ticker"] == "AAPL"
    assert any(e.message == "tool call get_quote" for e in logger.entries)


def test_tool_name_outside_allowlist_is_refused_not_executed() -> None:
    tool_turn = _message(
        [{"type": "tool_use", "id": "toolu_9", "name": "get_everything", "input": {}}],
        stop_reason="tool_use",
    )
    runner, messages, logger = _runner([tool_turn, _text(_valid_json())])
    outcome = runner.run("AAPL", BUNDLE)

    assert outcome.candidate is not None
    tool_result = messages.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert any("refused tool call get_everything" in e.message for e in logger.entries)


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_non_text_stop_reasons_count_as_schema_failures(stop_reason: str) -> None:
    runner, _, _ = _runner(
        [_message([], stop_reason=stop_reason), _message([], stop_reason=stop_reason)]
    )
    outcome = runner.run("AAPL", BUNDLE)
    assert outcome.candidate is None
    assert outcome.rejection_reason == SCHEMA_INVALID
