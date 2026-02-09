"""Credential encryption for email provider credentials (Fernet)."""

import base64
import json
from typing import Any, cast

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

DECRYPTION_ERROR_MSG = "Failed to decrypt credentials - invalid or corrupted data"


class CredentialEncryptor:
    """Encrypt/decrypt email credentials using Fernet (key derived from app secret)."""

    def __init__(self) -> None:
        self._fernet = Fernet(self._get_encryption_key())

    def _get_encryption_key(self) -> bytes:
        """Derive 32-byte key from secret_key + encryption_salt via PBKDF2-HMAC-SHA256."""
        settings = get_settings()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.encryption_salt.encode(),
            iterations=100_000,
        )
        key_material = settings.secret_key.encode()
        derived = kdf.derive(key_material)
        return base64.urlsafe_b64encode(derived)

    def encrypt(self, credentials: dict[str, Any]) -> str:
        """Encrypt credentials dict to a string safe for storage."""
        json_str = json.dumps(credentials)
        encrypted_bytes = self._fernet.encrypt(json_str.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted_str: str) -> dict[str, Any]:
        """Decrypt stored string back to credentials dict.

        Raises:
            ValueError: If invalid or not valid JSON.
        """
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_str.encode())
            json_str = decrypted_bytes.decode()
            result = json.loads(json_str)
            if not isinstance(result, dict):
                raise ValueError("Decrypted credentials must be a dictionary")
            return cast(dict[str, Any], result)
        except InvalidToken as e:
            raise ValueError(DECRYPTION_ERROR_MSG) from e
        except json.JSONDecodeError as e:
            raise ValueError("Decrypted credentials are not valid JSON") from e
