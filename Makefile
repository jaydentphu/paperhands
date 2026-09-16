.PHONY: install check run-daily

install:
	pip install -e ".[dev]"

check:
	python -m ruff check .
	python -m mypy --strict src
	python -m pytest

run-daily:
	python -m src.scheduler.daily_run
