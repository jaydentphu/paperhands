from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp.shared.auth import OAuthToken

from src.gateway.adapters.mcp_client import READ_TOOLS, FileTokenStorage, McpReadClient
from src.gateway.allowlist import CapabilityError


def test_call_rejects_non_read_tools_before_touching_the_network(tmp_path: Path) -> None:
    client = McpReadClient("http://127.0.0.1:1/mcp", tmp_path / "token.json")
    with pytest.raises(CapabilityError):
        client.call("not_a_read_tool", {})
    assert not (tmp_path / "token.json").exists()


def test_read_tools_are_all_getters() -> None:
    assert all(name.startswith("get_") for name in READ_TOOLS)


def test_file_token_storage_roundtrip(tmp_path: Path) -> None:
    storage = FileTokenStorage(tmp_path / "nested" / "token.json")
    assert not storage.has_tokens()
    assert asyncio.run(storage.get_tokens()) is None

    token = OAuthToken(
        access_token="unit-test", token_type="Bearer", refresh_token="r", expires_in=60
    )
    asyncio.run(storage.set_tokens(token))

    assert storage.has_tokens()
    loaded = asyncio.run(storage.get_tokens())
    assert loaded is not None
    assert loaded.refresh_token == "r"
    assert loaded.access_token == "unit-test"
