"""Envelope encryption and OAuth state signing for sensitive credentials."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any, cast

from cryptography.fernet import Fernet

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

    def _derive_master_key(self) -> bytes:
        """Derive master key from ENCRYPTION_SALT (use KMS in production)."""
        salt_bytes = self.settings.encryption_salt.encode()
        key = hashlib.pbkdf2_hmac(
            "sha256",
            salt_bytes,
            b"timeline_oauth_master_key",
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
        return hmac.new(
            self._master_key, payload.encode(), hashlib.sha256
        ).hexdigest()

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
            enc_dek_b64 = base64.urlsafe_b64encode(encrypted_dek).decode()
            enc_data_b64 = base64.urlsafe_b64encode(encrypted_data).decode()
            envelope = f"{key_id}:{enc_dek_b64}:{enc_data_b64}"
            signature = self._sign_payload(envelope)
            logger.debug("Encrypted data with key_id: %s", key_id)
            return f"{envelope}:{signature}"
        except Exception as e:
            logger.error("Encryption failed: %s", e, exc_info=True)
            raise ValueError(f"Encryption failed: {e}") from e

    def decrypt(self, encrypted_envelope: str) -> str | dict[str, Any]:
        """Decrypt envelope; returns dict if JSON else string.

        Raises:
            ValueError: Invalid format or signature.
        """
        try:
            parts = encrypted_envelope.split(":")
            if len(parts) != 4:
                raise ValueError("Invalid envelope format")
            key_id, enc_dek_b64, enc_data_b64, signature = parts
            envelope = f"{key_id}:{enc_dek_b64}:{enc_data_b64}"
            if not self._verify_signature(envelope, signature):
                raise ValueError("Invalid signature - data may be tampered")
            encrypted_dek = base64.urlsafe_b64decode(enc_dek_b64)
            encrypted_data = base64.urlsafe_b64decode(enc_data_b64)
            dek = self._decrypt_dek(encrypted_dek)
            data_bytes = Fernet(dek).decrypt(encrypted_data)
            data_str = data_bytes.decode()
            try:
                result = json.loads(data_str)
                return cast(dict[str, Any], result) if isinstance(result, dict) else data_str
            except json.JSONDecodeError:
                return data_str
        except Exception as e:
            logger.error("Decryption failed: %s", e, exc_info=True)
            raise ValueError(f"Decryption failed: {e}") from e

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


class OAuthStateManager:
    """Signed OAuth state (state_id:signature) for CSRF protection."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._signing_key = self.settings.secret_key.encode()

    def create_signed_state(self, state_id: str) -> str:
        """Return state_id:signature."""
        sig = hmac.new(self._signing_key, state_id.encode(), hashlib.sha256).hexdigest()
        return f"{state_id}:{sig}"

    def verify_and_extract(self, signed_state: str) -> str:
        """Verify signature and return state_id.

        Raises:
            ValueError: Invalid format or signature.
        """
        parts = signed_state.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid state format")
        state_id, signature = parts
        expected = hmac.new(
            self._signing_key, state_id.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid state signature - possible CSRF attack")
        return state_id
