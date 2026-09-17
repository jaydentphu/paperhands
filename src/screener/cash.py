"""Cohort A: hold cash. Records no_trade every run, unconditionally."""

from __future__ import annotations

from src.models.enums import Action


def decide() -> Action:
    return Action.NO_TRADE
