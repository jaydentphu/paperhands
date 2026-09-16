"""The only tools the research agent ever receives: the DataGateway's
allowlisted read functions, verbatim. No wrapping, no extras."""

from __future__ import annotations

from collections.abc import Callable

from src.gateway import DataGateway


def agent_tool_list(gateway: DataGateway) -> tuple[Callable[..., object], ...]:
    return gateway.tools()
