from backend.domain.services.auth_service import AuthService


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
