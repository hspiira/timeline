"""Password hashing (bcrypt with SHA-256 pre-hash).

Bcrypt truncates inputs at 72 bytes; pre-hashing with SHA-256 yields a fixed-length
input so long passwords are not silently truncated. Adopting this is a breaking
change for any existing bcrypt hashes stored without pre-hash.
"""

import base64
import hashlib

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
