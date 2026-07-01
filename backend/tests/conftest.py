import os
import uuid

import pytest

os.environ.setdefault("DEV_SKIP_AUTH", "true")

from backend.app import create_app
from backend.domain.entities.user import Role, User
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
    repo = UserRepository(db_session)
    user = User(id=uuid.uuid4(), email=f"test.{unique_name}@sywork.net", role=Role.RESOLVER, active=True)
    return repo.create(user)
