"""Tests for OAuthStateManager (envelope_encryption)."""

import pytest
from pydantic import SecretStr

from app.infrastructure.external.email.envelope_encryption import OAuthStateManager


@pytest.fixture
def oauth_state_manager(monkeypatch: pytest.MonkeyPatch) -> OAuthStateManager:
    """OAuthStateManager with a fixed secret for deterministic tests."""
    fake_settings = type("_", (), {"secret_key": SecretStr("test-secret-key-for-oauth-state-signing")})()
    monkeypatch.setattr(
        "app.infrastructure.external.email.envelope_encryption.get_settings",
        lambda: fake_settings,
    )
    return OAuthStateManager()


def test_create_signed_state_and_verify_roundtrip(oauth_state_manager: OAuthStateManager) -> None:
    """Roundtrip: create_signed_state then verify_and_extract returns original state_id."""
    state_id = "simple-state-id"
    signed = oauth_state_manager.create_signed_state(state_id)
    extracted = oauth_state_manager.verify_and_extract(signed)
    assert extracted == state_id


def test_state_id_containing_colon_roundtrip(oauth_state_manager: OAuthStateManager) -> None:
    """state_id may contain colons; verify_and_extract uses rsplit so it still works."""
    state_id = "tenant:123:redirect_uri:https://app.example/cb"
    signed = oauth_state_manager.create_signed_state(state_id)
    extracted = oauth_state_manager.verify_and_extract(signed)
    assert extracted == state_id


def test_verify_and_extract_invalid_format_rejects(oauth_state_manager: OAuthStateManager) -> None:
    """No colon in signed_state raises ValueError."""
    with pytest.raises(ValueError, match="Invalid state format"):
        oauth_state_manager.verify_and_extract("no-colon-here")
