"""Tests for the shared secure password generator."""

import string

import pytest

from app.infrastructure.security.password import (
    generate_secure_password,
    get_password_hash,
    verify_password,
)

SPECIAL = "!@#$%^&*-_=+"


def test_generated_password_has_every_required_character_class() -> None:
    """Every generated password contains lower, upper, digit and special."""
    for _ in range(200):
        pw = generate_secure_password()
        assert any(c in string.ascii_lowercase for c in pw)
        assert any(c in string.ascii_uppercase for c in pw)
        assert any(c in string.digits for c in pw)
        assert any(c in SPECIAL for c in pw)


def test_generated_password_respects_length() -> None:
    """Requested length is honoured."""
    assert len(generate_secure_password()) == 16
    assert len(generate_secure_password(24)) == 24


def test_generated_passwords_are_not_repeated() -> None:
    """Two calls do not return the same value."""
    assert len({generate_secure_password() for _ in range(100)}) == 100


def test_short_lengths_are_rejected() -> None:
    """A length that cannot hold all four classes is a programming error."""
    with pytest.raises(ValueError):
        generate_secure_password(4)


def test_generated_password_round_trips_through_hashing() -> None:
    """A generated password works with the real hasher."""
    pw = generate_secure_password()
    assert verify_password(pw, get_password_hash(pw))
