import uuid

import pytest

from backend.domain.entities.user import Role
from backend.domain.services.role_service import RoleService, RoleBusinessError


class FakeUser:
    def __init__(self, role):
        self.role = role


class FakeUsersRepo:
    def __init__(self, user=None, admin_count=1):
        self._user = user
        self._admin_count = admin_count

    def get_by_id(self, user_id):
        return self._user

    def count_active_admins(self):
        return self._admin_count


def test_promoting_to_admin_never_raises():
    svc = RoleService()
    svc.validate_role_change(uuid.uuid4(), Role.ADMIN, users_repo=FakeUsersRepo())


def test_demoting_last_admin_raises_409():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role=Role.ADMIN), admin_count=1)
    with pytest.raises(RoleBusinessError) as exc_info:
        svc.validate_role_change(uuid.uuid4(), Role.COORDINATOR, users_repo=repo)
    assert exc_info.value.code == "last_admin"
    assert exc_info.value.status_code == 409


def test_demoting_admin_when_other_admins_exist_passes():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role=Role.ADMIN), admin_count=2)
    svc.validate_role_change(uuid.uuid4(), Role.COORDINATOR, users_repo=repo)


def test_deactivating_last_admin_raises_409():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role=Role.ADMIN), admin_count=1)
    with pytest.raises(RoleBusinessError) as exc_info:
        svc.validate_deactivation(uuid.uuid4(), users_repo=repo)
    assert exc_info.value.code == "last_admin"


def test_deactivating_non_admin_never_raises():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role=Role.RESOLVER), admin_count=1)
    svc.validate_deactivation(uuid.uuid4(), users_repo=repo)
