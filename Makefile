# Repository root. Targets delegate to the application that owns them, so a
# command is defined once.

.PHONY: dev test test-all audit-deps

# Start the API and the web client together. One Ctrl-C stops both.
dev:
	$(MAKE) -C apps/api dev

# Backend tests that need no database.
test:
	$(MAKE) -C apps/api test

# All backend tests. Requires DATABASE_URL and a reachable Postgres.
test-all:
	$(MAKE) -C apps/api test-all

audit-deps:
	$(MAKE) -C apps/api audit-deps
