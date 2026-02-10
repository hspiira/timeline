"""Envelope encryption and OAuth state signing for sensitive credentials."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any, cast

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import get_settings
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class EnvelopeEncryptor:
    """Envelope encryption: DEK per credential, encrypted with MEK from ENCRYPTION_SALT.

    Format: key_id:encrypted_dek:encrypted_data:signature
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._master_key = self._derive_master_key()

    def _get_or_create_kdf_salt(self) -> bytes:
        """Return persisted KDF salt; if missing, generate and persist.

        Prefer ENCRYPTION_KDF_SALT (base64) from settings. Else read from
        ENCRYPTION_KDF_SALT_PATH or default path under storage_root; create
        file with a new random salt if missing.
        """
        if self.settings.encryption_kdf_salt:
            return base64.urlsafe_b64decode(self.settings.encryption_kdf_salt)
        path = self.settings.encryption_kdf_salt_path or os.path.join(
            self.settings.storage_root, ".encryption_kdf_salt"
        )
        if os.path.isfile(path):
            with open(path, "rb") as f:
                raw = f.read().strip()
            if raw:
                return base64.urlsafe_b64decode(raw)
        salt_bytes = secrets.token_bytes(32)
        encoded = base64.urlsafe_b64encode(salt_bytes).decode()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(encoded)
        logger.info(
            "Generated and persisted new KDF salt at %s (use ENCRYPTION_KDF_SALT or ENCRYPTION_KDF_SALT_PATH in production)",
            path,
        )
        return salt_bytes

    def _derive_master_key(self) -> bytes:
        """Derive master key from ENCRYPTION_SALT and a persisted KDF salt (use KMS in production)."""
        password = self.settings.encryption_salt.encode()
        salt = self._get_or_create_kdf_salt()
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password,
            salt,
            100000,
        )
        return base64.urlsafe_b64encode(key)

    def _generate_dek(self) -> bytes:
        """Generate new data encryption key."""
        return Fernet.generate_key()

    def _encrypt_dek(self, dek: bytes) -> bytes:
        """Encrypt DEK with master key."""
        return Fernet(self._master_key).encrypt(dek)

    def _decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        """Decrypt DEK with master key."""
        return Fernet(self._master_key).decrypt(encrypted_dek)

    def _generate_key_id(self) -> str:
        """Unique key identifier."""
        return f"dek_{utc_now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(8)}"

    def _sign_payload(self, payload: str) -> str:
        """HMAC signature of payload."""
        return hmac.new(self._master_key, payload.encode(), hashlib.sha256).hexdigest()

    def _verify_signature(self, payload: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self._sign_payload(payload)
        return hmac.compare_digest(expected, signature)

    def encrypt(self, data: str | dict[str, Any]) -> str:
        """Encrypt data; returns envelope string key_id:enc_dek:enc_data:signature."""
        try:
            data_str = json.dumps(data) if isinstance(data, dict) else str(data)
            dek = self._generate_dek()
            key_id = self._generate_key_id()
            fernet_dek = Fernet(dek)
            encrypted_data = fernet_dek.encrypt(data_str.encode())
            encrypted_dek = self._encrypt_dek(dek)
            # Fernet tokens are already url-safe base64; store as ASCII.
            enc_dek = encrypted_dek.decode()
            enc_data = encrypted_data.decode()
            envelope = f"{key_id}:{enc_dek}:{enc_data}"
            signature = self._sign_payload(envelope)
            logger.debug("Encrypted data with key_id: %s", key_id)
        except Exception as e:
            logger.exception("Encryption failed: %s", e)
            raise ValueError("Encryption failed") from e
        else:
            return f"{envelope}:{signature}"

    def decrypt(self, encrypted_envelope: str) -> str | dict[str, Any]:
        """Decrypt envelope; returns dict if JSON else string.

        Raises:
            ValueError: Invalid format or signature.
        """
        try:
            parts = encrypted_envelope.split(":")
            if len(parts) != 4:
                raise ValueError("Invalid envelope format")
            key_id, enc_dek, enc_data, signature = parts
            envelope = f"{key_id}:{enc_dek}:{enc_data}"
            if not self._verify_signature(envelope, signature):
                raise ValueError("Invalid signature - data may be tampered")
            encrypted_dek = enc_dek.encode()
            encrypted_data = enc_data.encode()
            dek = self._decrypt_dek(encrypted_dek)
            data_bytes = Fernet(dek).decrypt(encrypted_data)
            data_str = data_bytes.decode()
            try:
                result = json.loads(data_str)
                return (
                    cast(dict[str, Any], result)
                    if isinstance(result, dict)
                    else data_str
                )
            except json.JSONDecodeError:
                return data_str
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Decryption failed: %s", e)
            raise ValueError("Decryption failed") from e

    def rotate_key(self, encrypted_envelope: str) -> str:
        """Re-encrypt with new DEK (does not rotate MEK)."""
        data = self.decrypt(encrypted_envelope)
        return self.encrypt(data)

    def extract_key_id(self, encrypted_envelope: str) -> str:
        """Extract key ID without decrypting."""
        parts = encrypted_envelope.split(":")
        if len(parts) != 4:
            raise ValueError("Invalid envelope format")
        return parts[0]


# Domain-separation context for OAuth state signing key derivation.
_OAUTH_STATE_KEY_INFO = b"oauth-state-signing"


class OAuthStateManager:
    """Signed OAuth state (state_id:signature) for CSRF protection."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._signing_key = self._derive_signing_key()

    def _derive_signing_key(self) -> bytes:
        """Derive a purpose-specific HMAC key from the master secret (domain separation)."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=_OAUTH_STATE_KEY_INFO,
        )
        return hkdf.derive(self.settings.secret_key.encode())

    def create_signed_state(self, state_id: str) -> str:
        """Return state_id:signature."""
        sig = hmac.new(self._signing_key, state_id.encode(), hashlib.sha256).hexdigest()
        return f"{state_id}:{sig}"

    def verify_and_extract(self, signed_state: str) -> str:
        """Verify signature and return state_id.

        Splits on the last colon so state_id may contain colons.

        Raises:
            ValueError: Invalid format or signature.
        """
        parts = signed_state.rsplit(":", 1)
        if len(parts) != 2:
            raise ValueError("Invalid state format")
        state_id, signature = parts
        expected = hmac.new(
            self._signing_key, state_id.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid state signature - possible CSRF attack")
        return state_id
