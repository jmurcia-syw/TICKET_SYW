"""spec 038 US5 — "Notificar al Usuario" al crear una cuenta (correo de bienvenida HTML,
reutiliza el token de un solo uso + expiración de 30 min de "¿Olvidaste tu contraseña?", spec
003). Mockea el envío SMTP real — sin dependencia de un servidor de correo en el entorno de
prueba."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def _resolutor_role_id(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    return next(r["id"] for r in roles if r["name"] == "Resolutor")


def test_create_with_notify_true_sends_welcome_email_and_generates_token(client, unique_name):
    role_id = _resolutor_role_id(client)
    with patch("backend.api.routes.users.send_welcome_email") as mock_send:
        resp = client.post("/api/users", json={
            "email": f"notify.{unique_name}@sywork.net",
            "username": f"notify_{unique_name}",
            "role_id": role_id,
            "notify": True,
        })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["notification_sent"] is True
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.args
    assert call_kwargs[0] == f"notify.{unique_name}@sywork.net"
    assert call_kwargs[2] == body["provisional_password"]
    assert "token=" in call_kwargs[3]

    from backend.infra.database import get_db
    from backend.infra.repositories.user_repo import UserRepository
    created = UserRepository(get_db()).get_by_id(body["user"]["id"])
    assert created.reset_token is not None
    expires_at = created.reset_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    assert now < expires_at <= now + timedelta(minutes=31)


def test_create_with_notify_false_does_not_send_email(client, unique_name):
    role_id = _resolutor_role_id(client)
    with patch("backend.api.routes.users.send_welcome_email") as mock_send:
        resp = client.post("/api/users", json={
            "email": f"nonotify.{unique_name}@sywork.net",
            "username": f"nonotify_{unique_name}",
            "role_id": role_id,
        })
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["notification_sent"] is False
    mock_send.assert_not_called()


def test_create_with_notify_true_email_failure_does_not_revert_user_creation(client, unique_name):
    role_id = _resolutor_role_id(client)
    with patch("backend.api.routes.users.send_welcome_email", side_effect=RuntimeError("smtp down")):
        resp = client.post("/api/users", json={
            "email": f"failnotify.{unique_name}@sywork.net",
            "username": f"failnotify_{unique_name}",
            "role_id": role_id,
            "notify": True,
        })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["notification_sent"] is False

    # El usuario igual quedó creado y puede iniciar sesión con la contraseña provisional.
    login = client.post("/api/auth/login", json={
        "username_or_email": f"failnotify_{unique_name}",
        "password": body["provisional_password"],
    })
    assert login.status_code == 200
