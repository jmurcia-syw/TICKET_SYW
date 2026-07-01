import uuid

import pytest

from backend.app import create_app
from backend.domain.entities.user import User
from backend.infra.database import get_db
from backend.infra.repositories.user_repo import UserRepository


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def unique_name():
    """Short random suffix so repeated test runs never collide on unique constraints."""
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def db_session():
    session = next(get_db())
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
