from __future__ import annotations

from src.config import AdapterName
from src.gateway.adapter import Adapter
from src.gateway.adapters.fake import FakeAdapter
from src.gateway.adapters.robinhood import RobinhoodAdapter


def build_adapter(name: AdapterName) -> Adapter:
    if name == "robinhood":
        return RobinhoodAdapter()
    if name == "fake":
        return FakeAdapter()
    raise NotImplementedError(f"adapter '{name}' is not built in Phase 1 (see NOTES.md)")


def close_adapter(adapter: Adapter) -> None:
    close = getattr(adapter, "close", None)
    if callable(close):
        close()
