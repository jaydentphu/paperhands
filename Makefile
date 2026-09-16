.PHONY: install check run-daily run-snapshot robinhood-auth

install:
	pip install -e ".[dev]"

check:
	python -m ruff check .
	python -m mypy --strict src
	python -m pytest

run-daily:
	python -m src.scheduler.daily_run

run-snapshot:
	python -m src.scheduler.snapshot

robinhood-auth:
	python -m src.gateway.adapters.robinhood_auth
