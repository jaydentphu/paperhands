"""The complete set of names the research agent may ever call. PRD.md
section 7. Hardcoded on purpose: nothing reads this from config or env."""

from __future__ import annotations

from typing import Final

ALLOWLIST: Final[tuple[str, ...]] = (
    "get_quote",
    "get_option_chain",
    "get_historicals",
    "get_earnings_date",
    "get_news",
)


class CapabilityError(AttributeError):
    """Raised when anything outside ALLOWLIST is requested from the gateway."""

    def __init__(self, name: str) -> None:
        super().__init__(f"'{name}' is not in the DataGateway allowlist")
        self.name = name
