# Every target runs from this directory. There is one virtual environment at the
# root, the API is installed into it, and the tool configuration lives in
# pyproject.toml here, so `uv run <anything>` works from the root too.

.PHONY: help install dev test test-all lint typecheck check migrate revision web-check audit-deps

help:
	@echo "install     install both applications"
	@echo "dev         run the API and the web client together"
	@echo "test        backend tests that need no database"
	@echo "test-all    every backend test; needs DATABASE_URL"
	@echo "lint        flake8 and ruff over the API"
	@echo "typecheck   mypy over the API"
	@echo "check       lint, typecheck and test"
	@echo "web-check   the client's own gate: build, types, lint, unit tests"
	@echo "migrate     apply database migrations"
	@echo "revision    create a migration:  make revision m='what changed'"
	@echo "audit-deps  scan Python dependencies for known vulnerabilities"

install:
	uv sync --all-packages --all-extras
	pnpm install

dev:
	uv run python -m scripts.dev

test:
	uv run pytest -m "not requires_db"

test-all:
	uv run pytest

lint:
	uv run flake8 apps/api/app
	uv run ruff check apps/api/app

typecheck:
	uv run mypy

check: lint typecheck test

web-check:
	pnpm --filter ./apps/web verify

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(m)" || (echo "usage: make revision m='what changed'" && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

audit-deps:
	uv run pip-audit
