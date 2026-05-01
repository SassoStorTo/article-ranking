.PHONY: install build test lint typecheck dev check

install:
	uv sync
	npm --prefix frontend install

build:
	uv build
	npm --prefix frontend run build

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .
	npm --prefix frontend run lint

typecheck:
	uv run mypy app
	npm --prefix frontend run typecheck

dev:
	docker compose up --build

check: typecheck lint test
