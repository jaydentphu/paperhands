from src.config import HORIZON_DAYS, WATCHLIST, get_settings


def test_watchlist_has_five_tickers() -> None:
    assert len(WATCHLIST) == 5


def test_horizon_is_five_trading_days() -> None:
    assert HORIZON_DAYS == 5


def test_settings_load_without_env_file() -> None:
    settings = get_settings()
    assert settings.adapter == "robinhood"
