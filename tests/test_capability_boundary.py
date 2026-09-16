"""PRD.md section 7: the capability boundary.

This is the one file allowed to spell out the deny-list strings
(CLAUDE.md rule 2). Run with `pytest tests/test_capability_boundary.py -v`.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from src.agent.tools import agent_tool_list
from src.gateway import ALLOWLIST, DataGateway
from src.gateway.adapters.fake import FakeAdapter

ROOT = Path(__file__).resolve().parent.parent
FIVE_READ_FUNCTIONS = (
    "get_quote",
    "get_option_chain",
    "get_historicals",
    "get_earnings_date",
    "get_news",
)
DENY_LIST = (
    "place_option_order",
    "place_equity_order",
    "review_option_order",
    "cancel",
    "exercise",
)
FORBIDDEN_ENV_FRAGMENTS = ("EXEC", "TRADING", "AGENTIC")
SCANNED_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml"}


def _agent_tools() -> tuple[object, ...]:
    return agent_tool_list(DataGateway(FakeAdapter()))


def test_1_agent_tool_list_contains_only_the_five_read_functions() -> None:
    names = tuple(getattr(tool, "__name__", "") for tool in _agent_tools())
    assert names == FIVE_READ_FUNCTIONS
    assert ALLOWLIST == FIVE_READ_FUNCTIONS
    print(f"\nASSERTION 1: agent tool list is exactly {names}")


def test_2_no_tool_in_the_list_is_mutating() -> None:
    flags = {getattr(t, "__name__", ""): getattr(t, "is_mutating", True) for t in _agent_tools()}
    assert all(flag is False for flag in flags.values()), flags
    print(f"\nASSERTION 2: is_mutating flags {flags}")


def test_3_deny_list_strings_absent_from_agent_and_allowlist() -> None:
    files = [p for p in (ROOT / "src" / "agent").rglob("*") if p.is_file()]
    files.append(ROOT / "src" / "gateway" / "allowlist.py")
    scanned = 0
    for path in files:
        if "__pycache__" in path.parts or path.suffix not in SCANNED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for needle in DENY_LIST:
            assert needle not in text, f"{needle!r} found in {path.relative_to(ROOT)}"
        scanned += 1
    assert scanned >= 2
    print(f"\nASSERTION 3: none of {DENY_LIST} in {scanned} scanned files")


def test_4_worker_environment_has_no_execution_variables() -> None:
    names = _declared_worker_env_names()
    live = os.environ.get("SERVICE_ROLE") == "worker"
    if live:
        names |= set(os.environ)
    offending = sorted(
        n for n in names if any(frag in n.upper() for frag in FORBIDDEN_ENV_FRAGMENTS)
    )
    assert offending == [], offending
    print(
        f"\nASSERTION 4: {len(names)} worker env names "
        f"({'declared + live' if live else 'declared'}) contain none of "
        f"{FORBIDDEN_ENV_FRAGMENTS}"
    )


def _declared_worker_env_names() -> set[str]:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    worker = compose["services"]["worker"]
    names: set[str] = set()
    environment = worker.get("environment") or {}
    if isinstance(environment, dict):
        names |= {str(k) for k in environment}
    else:
        names |= {str(e).split("=", 1)[0] for e in environment}
    env_files = worker.get("env_file") or []
    if isinstance(env_files, str):
        env_files = [env_files]
    for name in [*env_files, ".env.example"]:
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                names.add(stripped.split("=", 1)[0].strip())
    return names
