import uuid

import pytest

from backend.app import create_app
from backend.domain.entities.user import User
from backend.infra.database import get_db
from backend.infra.repositories.user_repo import UserRepository


@pytest.fixture(scope="session")
def app():
    return create_app()


def _token_for_email(app, email: str) -> str:
    """JWT real para un usuario semilla, sin necesitar su contraseña."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        user = UserRepository(get_db()).get_by_email(email)
        assert user is not None, f"Usuario semilla {email} no existe (correr migraciones)"
        return create_access_token(identity=str(user.id))


@pytest.fixture(scope="session")
def admin_token(app):
    return _token_for_email(app, "admin@sywork.net")


@pytest.fixture(scope="session")
def coordinator_token(app):
    return _token_for_email(app, "coordinador@sywork.net")


@pytest.fixture(scope="session")
def qm_token(app):
    return _token_for_email(app, "qm@sywork.net")


@pytest.fixture(scope="session")
def resolver_token(app):
    return _token_for_email(app, "resolutor@sywork.net")


@pytest.fixture()
def client(app, admin_token):
    """Test client autenticado como Admin por defecto (FR-022: la API exige JWT).

    Los tests de enforcement usan `anon_client` o tokens de otros roles.
    """
    test_client = app.test_client()
    original_open = test_client.open

    def open_with_auth(*args, **kwargs):
        headers = kwargs.pop("headers", None) or {}
        if "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {admin_token}"
        kwargs["headers"] = headers
        return original_open(*args, **kwargs)

    test_client.open = open_with_auth
    return test_client


@pytest.fixture()
def anon_client(app):
    """Test client SIN autenticación, para validar 401."""
    return app.test_client()


@pytest.fixture()
def unique_name():
    """Short random suffix so repeated test runs never collide on unique constraints."""
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def db_session():
    session = get_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def resolver_user(db_session, unique_name):
    """A throwaway non-admin user for exercising /api/users mutation endpoints
    without touching real accounts or the last-admin business rule."""
    from backend.infra.repositories.role_repo import RoleRepository
    resolutor_role = RoleRepository(db_session).get_by_name("Resolutor")
    user = User(
        id=uuid.uuid4(), email=f"test.{unique_name}@sywork.net", username=f"test_{unique_name}",
        role=resolutor_role, active=True,
    )
    return UserRepository(db_session).create(user)
