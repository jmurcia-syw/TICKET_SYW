import uuid

from backend.domain.entities.user import User
from backend.domain.services.auth_service import AuthService
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.repositories.user_repo import UserRepository

_auth_svc = AuthService()


def _make_login_user(db_session, unique_name, role_name="Resolutor", password="Sywork2026!"):
    role = RoleRepository(db_session).get_by_name(role_name)
    user = User(
        id=uuid.uuid4(),
        email=f"login.{unique_name}@sywork.net",
        username=f"login_{unique_name}",
        role=role,
        active=True,
        password_hash=_auth_svc.hash_password(password),
    )
    return UserRepository(db_session).create(user)


def test_login_with_email_succeeds(client, db_session, unique_name):
    user = _make_login_user(db_session, unique_name)
    resp = client.post("/api/auth/login", json={"username_or_email": user.email, "password": "Sywork2026!"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "access_token" in body
    assert body["email"] == user.email
    assert body["username"] == user.username
    assert body["role"]["name"] == "Resolutor"
    assert isinstance(body["permissions"], list)
    assert {"module": "clients", "action": "view"} in body["permissions"]


def test_login_with_username_succeeds(client, db_session, unique_name):
    user = _make_login_user(db_session, unique_name)
    resp = client.post("/api/auth/login", json={"username_or_email": user.username, "password": "Sywork2026!"})
    assert resp.status_code == 200


def test_login_with_wrong_password_returns_401(client, db_session, unique_name):
    user = _make_login_user(db_session, unique_name)
    resp = client.post("/api/auth/login", json={"username_or_email": user.email, "password": "wrong"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "unauthorized"


def test_login_with_unknown_identifier_returns_401(client):
    resp = client.post("/api/auth/login", json={"username_or_email": "nobody@sywork.net", "password": "x"})
    assert resp.status_code == 401


def test_login_missing_fields_returns_400(client):
    resp = client.post("/api/auth/login", json={"username_or_email": "a@sywork.net"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_me_requires_a_valid_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_role_and_permissions_for_logged_in_user(client, db_session, unique_name):
    user = _make_login_user(db_session, unique_name)
    login = client.post("/api/auth/login", json={"username_or_email": user.email, "password": "Sywork2026!"}).get_json()
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["email"] == user.email
    assert body["role"]["name"] == "Resolutor"
