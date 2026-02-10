"""Gmail OAuth helper (authorize and store tokens). Stub for Phase 9.

Usage:
    uv run python -m scripts.gmail_oauth_helper [--tenant-id ID] [--redirect-uri URI]
Implement using app.infrastructure.external.email.oauth_drivers and app core config.
All imports must use app.*.
"""

import sys


def main() -> None:
    """Print usage until implemented."""
    print(
        "gmail_oauth_helper: use app.infrastructure.external.email.oauth_drivers and app.core.config",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
