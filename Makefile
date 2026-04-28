.PHONY: install build test lint format-check typecheck dev check

install:
	uv sync

build:
	uv build

test:
	uv run python -m pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy

dev:
	uv run python -c "from news_ranker import health; print(health())"

check: typecheck lint test
