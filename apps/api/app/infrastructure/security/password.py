"""Password hashing (bcrypt with SHA-256 pre-hash).

Bcrypt truncates inputs at 72 bytes; pre-hashing with SHA-256 yields a fixed-length
input so long passwords are not silently truncated. Adopting this is a breaking
change for any existing bcrypt hashes stored without pre-hash.
"""

import base64
import hashlib
import secrets
import string

import bcrypt


def _prehash(password: str) -> bytes:
    """SHA-256 pre-hash to avoid bcrypt's 72-byte truncation."""
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches hashed_password."""
    try:
        result = bcrypt.checkpw(
            _prehash(plain_password),
            hashed_password.encode("utf-8"),
        )
        return bool(result)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Return bcrypt hash of password (SHA-256 pre-hashed before bcrypt)."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(_prehash(password), salt)
    return hashed.decode("utf-8")


def generate_secure_password(length: int = 16) -> str:
    """Return a cryptographically secure password with guaranteed complexity.

    Guarantees at least one lowercase, one uppercase, one digit and one special
    character; remaining positions come from the full alphabet, then the whole
    string is shuffled so the guaranteed characters are not always first.

    Used where the system must set a password nobody is meant to know (operator
    tenant provisioning, invited members): the account is reached through a
    one-time token instead.
    """
    if length < 8:
        raise ValueError("Generated passwords must be at least 8 characters")
    special = "!@#$%^&*-_=+"
    alphabet = string.ascii_letters + string.digits + special
    rng = secrets.SystemRandom()
    chars = [
        rng.choice(string.ascii_lowercase),
        rng.choice(string.ascii_uppercase),
        rng.choice(string.digits),
        rng.choice(special),
    ]
    chars += [rng.choice(alphabet) for _ in range(length - len(chars))]
    rng.shuffle(chars)
    return "".join(chars)
