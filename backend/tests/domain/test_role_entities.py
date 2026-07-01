import uuid

from backend.domain.entities.role import Role, Permission
from backend.domain.entities.user import User


def test_role_create_generates_id_and_defaults():
    role = Role.create("Coordinador", description="Gestiona clientes y proyectos")
    assert isinstance(role.id, uuid.UUID)
    assert role.name == "Coordinador"
    assert role.description == "Gestiona clientes y proyectos"
    assert role.active is True


def test_permission_create_generates_id():
    perm = Permission.create("clients", "view")
    assert isinstance(perm.id, uuid.UUID)
    assert perm.module == "clients"
    assert perm.action == "view"


def test_user_has_role_checks_role_name():
    role = Role.create("Admin")
    user = User(id=uuid.uuid4(), email="a@sywork.net", username="a", role=role)
    assert user.has_role("Admin", "Coordinador") is True
    assert user.has_role("QM") is False


def test_user_can_access_sensitive_data_for_admin_and_coordinador():
    admin_user = User(id=uuid.uuid4(), email="a@sywork.net", username="a", role=Role.create("Admin"))
    resolutor_user = User(id=uuid.uuid4(), email="r@sywork.net", username="r", role=Role.create("Resolutor"))
    assert admin_user.can_access_sensitive_data() is True
    assert resolutor_user.can_access_sensitive_data() is False
