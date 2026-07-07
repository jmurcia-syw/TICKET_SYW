import uuid
from datetime import datetime, timedelta, timezone

from backend.domain.entities.role import Role
from backend.domain.entities.user import User
from backend.domain.services.auth_service import AuthService


def _user(**overrides) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        email="reset.test@sywork.net",
        username="reset_test",
        role=Role(id=uuid.uuid4(), name="Resolutor"),
        active=True,
    )
    defaults.update(overrides)
    return User(**defaults)


def test_hash_password_is_not_the_plaintext():
    svc = AuthService()
    hashed = svc.hash_password("Sywork2026!")
    assert hashed != "Sywork2026!"
    assert len(hashed) > 20


def test_verify_password_accepts_correct_password():
    svc = AuthService()
    hashed = svc.hash_password("Sywork2026!")
    assert svc.verify_password("Sywork2026!", hashed) is True


def test_verify_password_rejects_wrong_password():
    svc = AuthService()
    hashed = svc.hash_password("Sywork2026!")
    assert svc.verify_password("wrong-password", hashed) is False


def test_verify_password_handles_missing_hash():
    svc = AuthService()
    assert svc.verify_password("anything", None) is False
    assert svc.verify_password("anything", "") is False


def test_generate_reset_token_expires_in_30_minutes():
    svc = AuthService()
    token, expires_at = svc.generate_reset_token()
    assert isinstance(token, str) and len(token) > 20
    delta = expires_at - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < delta <= timedelta(minutes=30)


def test_reset_token_valid_when_matching_and_not_expired():
    svc = AuthService()
    token, expires_at = svc.generate_reset_token()
    user = _user(reset_token=token, reset_token_expires_at=expires_at)
    assert svc.is_reset_token_valid(user, token) is True


def test_reset_token_invalid_when_expired():
    svc = AuthService()
    token = "some-token"
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    user = _user(reset_token=token, reset_token_expires_at=expired_at)
    assert svc.is_reset_token_valid(user, token) is False


def test_reset_token_invalid_when_reused_after_clearing():
    svc = AuthService()
    token, expires_at = svc.generate_reset_token()
    user = _user(reset_token=None, reset_token_expires_at=None)
    assert svc.is_reset_token_valid(user, token) is False


def test_reset_token_invalid_for_inactive_account():
    svc = AuthService()
    token, expires_at = svc.generate_reset_token()
    user = _user(active=False, reset_token=token, reset_token_expires_at=expires_at)
    assert svc.is_reset_token_valid(user, token) is False


def test_reset_token_invalid_when_token_does_not_match():
    svc = AuthService()
    token, expires_at = svc.generate_reset_token()
    user = _user(reset_token=token, reset_token_expires_at=expires_at)
    assert svc.is_reset_token_valid(user, "wrong-token") is False
