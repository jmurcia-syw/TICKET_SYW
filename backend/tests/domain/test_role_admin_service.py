import uuid

import pytest

from backend.domain.services.role_admin_service import RoleAdminService, RoleAdminError


class FakeRole:
    def __init__(self, id_, name):
        self.id = id_
        self.name = name


class FakeUsersRepo:
    def __init__(self, active_count=0):
        self._active_count = active_count

    def count_active_users_with_role(self, role_id):
        return self._active_count


class FakeRolesRepo:
    def __init__(self, role_count=0):
        self._role_count = role_count

    def count_roles_with_permission(self, permission_id):
        return self._role_count


def test_cannot_deactivate_admin_role():
    svc = RoleAdminService()
    with pytest.raises(RoleAdminError) as exc_info:
        svc.validate_deactivation(FakeRole(uuid.uuid4(), "Admin"), users_repo=FakeUsersRepo(active_count=0))
    err = exc_info.value
    assert err.code == "cannot_deactivate_admin_role"
    assert err.status_code == 409


def test_cannot_deactivate_role_with_active_users():
    svc = RoleAdminService()
    with pytest.raises(RoleAdminError) as exc_info:
        svc.validate_deactivation(FakeRole(uuid.uuid4(), "Coordinador"), users_repo=FakeUsersRepo(active_count=2))
    err = exc_info.value
    assert err.code == "role_in_use"
    assert err.status_code == 409
    assert err.extra == {"active_users_count": 2}


def test_can_deactivate_role_with_no_active_users():
    svc = RoleAdminService()
    svc.validate_deactivation(FakeRole(uuid.uuid4(), "Coordinador"), users_repo=FakeUsersRepo(active_count=0))


def test_cannot_delete_permission_assigned_to_a_role():
    svc = RoleAdminService()
    with pytest.raises(RoleAdminError) as exc_info:
        svc.validate_permission_delete(uuid.uuid4(), roles_repo=FakeRolesRepo(role_count=1))
    err = exc_info.value
    assert err.code == "permission_in_use"
    assert err.status_code == 409
    assert err.extra == {"role_count": 1}


def test_can_delete_unused_permission():
    svc = RoleAdminService()
    svc.validate_permission_delete(uuid.uuid4(), roles_repo=FakeRolesRepo(role_count=0))
