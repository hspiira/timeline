# Timeline project Makefile (optional)
# Run: make <target>

.PHONY: audit-deps test

# Run pip-audit to check for known vulnerabilities (install: uv add --dev pip-audit).
audit-deps:
	uv run pip-audit

# Run tests (excluding requires_db by default so no DB required).
test:
	uv run pytest -m "not requires_db" -v

# Run all tests (requires Postgres: DATABASE_BACKEND=postgres, DATABASE_URL set).
test-all:
	uv run pytest -v
