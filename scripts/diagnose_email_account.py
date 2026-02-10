"""Diagnose email account (OAuth/sync status). Stub for Phase 9.

Usage:
    uv run python -m scripts.diagnose_email_account <tenant_id> <email_account_id>
Implement using app.infrastructure.persistence.repositories and email account model.
All imports must use app.*.
"""

import sys


# Stub: full implementation would load tenant + email account and print sync/oauth status.
def main() -> None:
    """Print usage until implemented."""
    if len(sys.argv) < 3:
        print(
            "Usage: uv run python -m scripts.diagnose_email_account <tenant_id> <email_account_id>",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        "diagnose_email_account: use app.infrastructure.persistence.repositories and EmailAccount model",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
