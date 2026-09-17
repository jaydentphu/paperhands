"""Runs the Cohort C agent for one ticker.

Calls the model with structured output plus the five gateway tools, owns
the tool loop, retries once when the output fails the TradeCandidate schema,
and on the second failure returns a schema_invalid rejection (which the
caller records as no_trade). Every prompt, response, and tool call goes
through the redacting LogSink.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
from anthropic.types import Message
from pydantic import ValidationError

from src.agent.prompt import SYSTEM_PROMPT, retry_message, user_message
from src.agent.schema import OUTPUT_SCHEMA, TradeCandidate
from src.agent.tools import dispatch, tool_definitions
from src.gateway import CapabilityError, DataGateway
from src.logging import LogSink
from src.models.enums import LogLevel

SCHEMA_INVALID = "schema_invalid"
DEFAULT_MODEL = "claude-sonnet-5"
COMPONENT = "agent"


class MessagesAPI(Protocol):
    def create(self, **kwargs: Any) -> Message: ...


class SdkMessages:
    """Adapts the SDK's overloaded Messages.create to the MessagesAPI shape.
    Only the non-streaming form is ever used."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def create(self, **kwargs: Any) -> Message:
        return self._client.messages.create(
            model=kwargs["model"],
            max_tokens=kwargs["max_tokens"],
            system=kwargs["system"],
            messages=kwargs["messages"],
            tools=kwargs["tools"],
            output_config=kwargs["output_config"],
        )


@dataclass(frozen=True)
class AgentOutcome:
    ticker: str
    candidate: TradeCandidate | None
    rejection_reason: str | None
    attempts: int
    response_text: str | None


class AgentRunner:
    def __init__(
        self,
        messages: MessagesAPI,
        gateway: DataGateway,
        logger: LogSink,
        model: str = DEFAULT_MODEL,
        max_tool_rounds: int = 6,
        max_tokens: int = 16000,
    ) -> None:
        self._messages = messages
        self._gateway = gateway
        self._logger = logger
        self._model = model
        self._max_tool_rounds = max_tool_rounds
        self._max_tokens = max_tokens
        self._tools = tool_definitions()

    def run(self, ticker: str, bundle_text: str) -> AgentOutcome:
        conversation: list[dict[str, Any]] = [
            {"role": "user", "content": user_message(bundle_text)}
        ]
        self._logger.log(
            LogLevel.INFO,
            COMPONENT,
            f"prompt for {ticker}",
            {"model": self._model, "system": SYSTEM_PROMPT, "user": conversation[0]["content"]},
        )
        text: str | None = None
        error = ""
        for attempt in (1, 2):
            if attempt == 2:
                conversation.append({"role": "user", "content": retry_message(error)})
            text = self._complete(ticker, conversation, attempt)
            candidate, error = self._parse(ticker, text)
            if candidate is not None:
                self._logger.log(
                    LogLevel.INFO,
                    COMPONENT,
                    f"candidate accepted by schema for {ticker} on attempt {attempt}",
                    {"candidate": candidate.model_dump(mode="json")},
                )
                return AgentOutcome(ticker, candidate, None, attempt, text)
            self._logger.log(
                LogLevel.WARNING,
                COMPONENT,
                f"schema failure for {ticker} on attempt {attempt}: {error}",
                {"response_text": text},
            )
        self._logger.log(
            LogLevel.ERROR,
            COMPONENT,
            f"{ticker}: rejected after 2 attempts, recording no_trade ({SCHEMA_INVALID})",
            None,
        )
        return AgentOutcome(ticker, None, SCHEMA_INVALID, 2, text)

    def _complete(
        self, ticker: str, conversation: list[dict[str, Any]], attempt: int
    ) -> str | None:
        for round_no in range(self._max_tool_rounds + 1):
            response = self._messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=conversation,
                tools=self._tools,
                output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            )
            content_dicts = [block.model_dump(mode="json") for block in response.content]
            conversation.append({"role": "assistant", "content": list(response.content)})
            self._logger.log(
                LogLevel.INFO,
                COMPONENT,
                f"response for {ticker} attempt {attempt} round {round_no}",
                {
                    "stop_reason": response.stop_reason,
                    "content": content_dicts,
                    "usage": response.usage.model_dump(mode="json") if response.usage else None,
                },
            )
            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text")
                return text or None
            results = [
                self._call_tool(b.id, b.name, b.input)
                for b in response.content
                if b.type == "tool_use"
            ]
            conversation.append({"role": "user", "content": results})
        self._logger.log(
            LogLevel.WARNING, COMPONENT, f"{ticker}: tool round limit reached", None
        )
        return None

    def _call_tool(self, tool_use_id: str, name: str, arguments: object) -> dict[str, Any]:
        args = arguments if isinstance(arguments, dict) else {}
        try:
            content = dispatch(self._gateway, name, args)
            self._logger.log(
                LogLevel.INFO,
                COMPONENT,
                f"tool call {name}",
                {"arguments": args, "result_chars": len(content)},
            )
            return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
        except CapabilityError as exc:
            self._logger.log(
                LogLevel.WARNING, COMPONENT, f"refused tool call {name}: {exc}", {"arguments": args}
            )
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": f"tool '{name}' is not available",
                "is_error": True,
            }
        except Exception as exc:
            self._logger.log(
                LogLevel.WARNING, COMPONENT, f"tool call {name} failed: {exc}", {"arguments": args}
            )
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": f"tool '{name}' failed: {exc}",
                "is_error": True,
            }

    @staticmethod
    def _parse(ticker: str, text: str | None) -> tuple[TradeCandidate | None, str]:
        if not text:
            return None, "no text output from the model"
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f"response is not valid JSON ({exc.msg})"
        try:
            candidate = TradeCandidate.model_validate(data)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
            )
            return None, problems or "schema validation failed"
        if candidate.ticker != ticker:
            return None, f"ticker must be {ticker}, got {candidate.ticker}"
        return candidate, ""
