"""Password hashing (bcrypt)."""

import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches hashed_password."""
    try:
        result = bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
        return bool(result)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Return bcrypt hash of password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")
