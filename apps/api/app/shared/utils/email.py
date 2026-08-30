"""Email address helpers.

Lives in ``shared`` rather than beside the ORM model so the application layer can
use it without importing infrastructure (see docs/ARCHITECTURE.md § layering).
"""


def normalise_email(email: str) -> str:
    """Return the storage form of an email address: trimmed and lower-cased.

    Identity emails are unique across the whole system, and that constraint is on
    the stored value, so ``Henry@x`` and ``henry@x`` must not become two people.
    Apply this before writing or looking up an email.
    """
    return email.strip().lower()
