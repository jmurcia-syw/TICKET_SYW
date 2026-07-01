# Roles, Permisos y Login Provisional — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed 4-role enum with dynamic, DB-backed roles and permissions (module + action granularity), add a provisional username/password login endpoint that coexists with the existing Google OAuth login, and seed 4 roles + 4 users with distinct permission profiles.

**Architecture:** Follows the existing layered pattern used by every other maestro in this codebase exactly: domain entity (dataclass) → domain service (business rules, raises `DomainError` subclasses) → SQLAlchemy model + repository → Flask-RESTX route. New tables (`roles`, `permissions`, `role_permissions`) plus an in-place migration of `users` off its fixed-text `role` column onto a `role_id` FK, with new `username`/`password_hash` columns. Backend enforcement of permissions is explicitly **out of scope** for this plan — the new API routes stay unauthenticated, same as clients/projects/resources/users/skills today. Only `/api/auth/login` and `/api/auth/me` involve real JWT auth.

**Tech Stack:** Flask, Flask-RESTX, SQLAlchemy, Alembic, PostgreSQL, Werkzeug (`werkzeug.security` for password hashing — already a Flask dependency, no new package), pytest.

## Global Constraints

- Every new API error response uses the existing `{"error": code, "message": ...}` shape via `backend.api.routes._shared.error_model`/`server_error` (see `backend/api/routes/clients.py` for the reference pattern).
- Every `DomainError` subclass carries its own `status_code` (see `backend/domain/errors.py`) — do not hardcode `409` in route except-clauses; use `e.status_code`.
- POST-create endpoints return a `Location` header pointing at the created resource (see `backend/api/routes/clients.py::ClientList.post`).
- Soft-deletable resources (`roles`) use `PATCH .../deactivate` and `/activate`, never a hard `DELETE`. Catalog-style resources (`permissions`) use a hard `DELETE`, blocked with `409` if in use — same pattern as `backend/api/routes/resources.py::SkillDetail.delete`.
- Backend routes for maestros (including the new `roles`/`permissions` routes) do **not** require JWT. Do not add `@jwt_required_active` or `@require_role` to them.
- All new backend code targets Python 3.12 (matches the running container).
- Run all commands via `docker exec sywork_backend ...` — the container mounts the repo live, no rebuild needed for Python file changes.
- Test working directory inside the container is `/repo/backend`, so pytest paths are relative to that (e.g. `pytest tests/domain/test_x.py`).

## Critical Sequencing Note (read before starting)

`backend/domain/entities/user.py` currently defines `Role(str, Enum)`, and it is imported at the **top level** (module-load time, not inside a function) by five files: `backend/tests/conftest.py`, `backend/infra/repositories/user_repo.py`, `backend/infra/models/user_model.py`, `backend/api/routes/users.py`, `backend/api/routes/auth.py`, plus `backend/domain/services/role_service.py` and `backend/api/middleware/{auth,rbac}.py`. `pytest` auto-imports `backend/tests/conftest.py` for **every** test collected anywhere under `backend/tests/`, and `conftest.py` transitively imports `user_repo.py` → `user_model.py`.

This means: the moment Task 1 removes the old `Role` enum from `user.py`, **no `pytest` command anywhere in this repo will succeed** — not even for an unrelated test file — until every file in that import chain has been fixed. Tasks 1-8 below therefore write code and verify it with `py_compile` / `python -c "import ..."` only, **not** `pytest`. The first `pytest` run happens in Task 8, once the whole chain is consistent again. This is intentional, not an oversight — do not try to run `pytest` earlier than Task 8 even if it seems like a step should have a test-passes checkpoint.

---

### Task 1: Role & Permission domain entities, User entity update

**Files:**
- Create: `backend/domain/entities/role.py`
- Modify: `backend/domain/entities/user.py`
- Test: `backend/tests/domain/test_role_entities.py` (written now, run in Task 8)

**Interfaces:**
- Produces: `Role(id, name, description=None, active=True, created_at=...)` with `Role.create(name, description=None)`; `Permission(id, module, action, description=None)` with `Permission.create(module, action, description=None)`. `User` gains `username: str`, `password_hash: Optional[str] = None`, and `role: Role` (was `Role` enum member, now the dataclass above). `User.has_role(*role_names: str)` and `User.can_access_sensitive_data()` now compare `self.role.name` against strings, not enum members.

- [ ] **Step 1: Write the test (will not run until Task 8 — see Critical Sequencing Note above)**

Create `backend/tests/domain/test_role_entities.py`:

```python
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
```

- [ ] **Step 2: Create the Role/Permission entities**

Create `backend/domain/entities/role.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Role:
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, name: str, description: Optional[str] = None) -> "Role":
        return cls(id=uuid.uuid4(), name=name, description=description)


@dataclass
class Permission:
    id: uuid.UUID
    module: str
    action: str
    description: Optional[str] = None

    @classmethod
    def create(cls, module: str, action: str, description: Optional[str] = None) -> "Permission":
        return cls(id=uuid.uuid4(), module=module, action=action, description=description)
```

- [ ] **Step 3: Update the User entity**

Replace the full contents of `backend/domain/entities/user.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from backend.domain.entities.role import Role


@dataclass
class User:
    id: uuid.UUID
    email: str
    username: str
    role: Role
    active: bool = True
    google_sub: Optional[str] = None
    password_hash: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def has_role(self, *role_names: str) -> bool:
        return self.role.name in role_names

    def can_access_sensitive_data(self) -> bool:
        return self.role.name in ("Admin", "Coordinador")
```

This removes the `Role(str, Enum)` class that used to live here. Per the Critical Sequencing Note, this breaks several other files' imports until Task 8 — that is expected.

- [ ] **Step 4: Byte-compile the new/changed files (do NOT run pytest yet)**

Run: `docker exec sywork_backend python -m py_compile backend/domain/entities/role.py backend/domain/entities/user.py`
Expected: no output (success)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/entities/role.py backend/domain/entities/user.py backend/tests/domain/test_role_entities.py
git commit -m "feat(domain): add Role/Permission entities, move User off fixed Role enum"
```

---

### Task 2: AuthService — password hashing

**Files:**
- Create: `backend/domain/services/auth_service.py`
- Test: `backend/tests/domain/test_auth_service.py` (written now, run in Task 8)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `AuthService.hash_password(password: str) -> str`, `AuthService.verify_password(password: str, password_hash: Optional[str]) -> bool`. Used by Task 6 (migration seed) and Task 7 (login route).

- [ ] **Step 1: Write the test**

Create `backend/tests/domain/test_auth_service.py`:

```python
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
```

- [ ] **Step 2: Implement AuthService**

Create `backend/domain/services/auth_service.py`:

```python
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash


class AuthService:
    def hash_password(self, password: str) -> str:
        return generate_password_hash(password)

    def verify_password(self, password: str, password_hash: Optional[str]) -> bool:
        if not password_hash:
            return False
        return check_password_hash(password_hash, password)
```

- [ ] **Step 3: Byte-compile**

Run: `docker exec sywork_backend python -m py_compile backend/domain/services/auth_service.py`
Expected: no output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/domain/services/auth_service.py backend/tests/domain/test_auth_service.py
git commit -m "feat(domain): add AuthService for provisional login password hashing"
```

---

### Task 3: RoleAdminService — role/permission business rules

**Files:**
- Create: `backend/domain/services/role_admin_service.py`
- Test: `backend/tests/domain/test_role_admin_service.py` (written now, run in Task 8)

**Interfaces:**
- Consumes: `backend.domain.errors.DomainError` (existing, from `backend/domain/errors.py`).
- Produces: `RoleAdminError(DomainError)`; `RoleAdminService.validate_deactivation(role, users_repo=None)` (raises if `role.name == "Admin"` or if the role has active users, both `status_code=409`); `RoleAdminService.validate_permission_delete(permission_id, roles_repo=None)` (raises `status_code=409` if any role still has that permission assigned). Used by Task 9 (roles route) and Task 10 (permissions route).

- [ ] **Step 1: Write the test**

Create `backend/tests/domain/test_role_admin_service.py`:

```python
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
```

- [ ] **Step 2: Implement RoleAdminService**

Create `backend/domain/services/role_admin_service.py`:

```python
import uuid
from backend.domain.errors import DomainError


class RoleAdminError(DomainError):
    pass


class RoleAdminService:
    ADMIN_ROLE_NAME = "Admin"

    def validate_deactivation(self, role, users_repo=None) -> None:
        if role.name == self.ADMIN_ROLE_NAME:
            raise RoleAdminError("cannot_deactivate_admin_role", "El rol Admin no se puede desactivar")
        if users_repo:
            count = users_repo.count_active_users_with_role(role.id)
            if count > 0:
                raise RoleAdminError(
                    "role_in_use", f"El rol tiene {count} usuario(s) activo(s) asignado(s)",
                    active_users_count=count,
                )

    def validate_permission_delete(self, permission_id: uuid.UUID, roles_repo=None) -> None:
        if roles_repo:
            count = roles_repo.count_roles_with_permission(permission_id)
            if count > 0:
                raise RoleAdminError(
                    "permission_in_use", f"El permiso está asignado a {count} rol(es)",
                    role_count=count,
                )
```

- [ ] **Step 3: Byte-compile**

Run: `docker exec sywork_backend python -m py_compile backend/domain/services/role_admin_service.py`
Expected: no output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/domain/services/role_admin_service.py backend/tests/domain/test_role_admin_service.py
git commit -m "feat(domain): add RoleAdminService business rules for roles/permissions"
```

---

### Task 4: Fix RoleService for dynamic roles

**Files:**
- Modify: `backend/domain/services/role_service.py`
- Modify: `backend/tests/domain/test_role_service.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `RoleService.validate_role_change(user_id, new_role_name: str, users_repo=None)`, `RoleService.validate_deactivation(user_id, users_repo=None)` — same method names as before, but `validate_role_change`'s second parameter is now a plain `str` (the target role's `name`) instead of the old `Role` enum member. Callers (Task 9's users.py update, folded into Task 8) must resolve the role name before calling this.

- [ ] **Step 1: Update the test**

Replace the full contents of `backend/tests/domain/test_role_service.py`:

```python
import uuid

import pytest

from backend.domain.services.role_service import RoleService, RoleBusinessError


class FakeRole:
    def __init__(self, name):
        self.name = name


class FakeUser:
    def __init__(self, role_name):
        self.role = FakeRole(role_name)


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
    svc.validate_role_change(uuid.uuid4(), "Admin", users_repo=FakeUsersRepo())


def test_demoting_last_admin_raises_409():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role_name="Admin"), admin_count=1)
    with pytest.raises(RoleBusinessError) as exc_info:
        svc.validate_role_change(uuid.uuid4(), "Coordinador", users_repo=repo)
    assert exc_info.value.code == "last_admin"
    assert exc_info.value.status_code == 409


def test_demoting_admin_when_other_admins_exist_passes():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role_name="Admin"), admin_count=2)
    svc.validate_role_change(uuid.uuid4(), "Coordinador", users_repo=repo)


def test_deactivating_last_admin_raises_409():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role_name="Admin"), admin_count=1)
    with pytest.raises(RoleBusinessError) as exc_info:
        svc.validate_deactivation(uuid.uuid4(), users_repo=repo)
    assert exc_info.value.code == "last_admin"


def test_deactivating_non_admin_never_raises():
    svc = RoleService()
    repo = FakeUsersRepo(user=FakeUser(role_name="Resolutor"), admin_count=1)
    svc.validate_deactivation(uuid.uuid4(), users_repo=repo)
```

- [ ] **Step 2: Fix RoleService**

Replace the full contents of `backend/domain/services/role_service.py`:

```python
import uuid
from backend.domain.errors import DomainError


class RoleBusinessError(DomainError):
    pass


class RoleService:
    ADMIN_ROLE_NAME = "Admin"

    def validate_role_change(self, user_id: uuid.UUID, new_role_name: str, users_repo=None) -> None:
        if new_role_name == self.ADMIN_ROLE_NAME:
            return
        if users_repo:
            user = users_repo.get_by_id(user_id)
            if user and user.role.name == self.ADMIN_ROLE_NAME:
                admin_count = users_repo.count_active_admins()
                if admin_count <= 1:
                    raise RoleBusinessError("last_admin", "No se puede cambiar el rol del último Admin activo")

    def validate_deactivation(self, user_id: uuid.UUID, users_repo=None) -> None:
        if users_repo:
            user = users_repo.get_by_id(user_id)
            if user and user.role.name == self.ADMIN_ROLE_NAME:
                admin_count = users_repo.count_active_admins()
                if admin_count <= 1:
                    raise RoleBusinessError("last_admin", "No se puede desactivar al último Admin activo")
```

- [ ] **Step 3: Byte-compile**

Run: `docker exec sywork_backend python -m py_compile backend/domain/services/role_service.py`
Expected: no output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/domain/services/role_service.py backend/tests/domain/test_role_service.py
git commit -m "fix(domain): adapt RoleService last-admin protection to dynamic roles"
```

---

### Task 5: SQLAlchemy models — RoleModel, PermissionModel, role_permissions; UserModel update

**Files:**
- Create: `backend/infra/models/role_model.py`
- Modify: `backend/infra/models/user_model.py`
- Modify: `backend/infra/models/__init__.py`

**Interfaces:**
- Consumes: `Role`/`Permission` from Task 1, `User` from Task 1.
- Produces: `RoleModel`, `PermissionModel`, `role_permissions_table` (SQLAlchemy `Table`), both models expose `.to_entity()`. `UserModel` gains `role_id`, `username`, `password_hash` columns and a `role` relationship (`lazy="joined"`, mirrors `ResourceModel.skills` in `backend/infra/models/resource_model.py`); `UserModel.to_entity()`/`.from_entity()` updated for the new shape.

- [ ] **Step 1: Create the Role/Permission models**

Create `backend/infra/models/role_model.py`:

```python
import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Table, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.role import Role, Permission

role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
)


class PermissionModel(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    module = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    def to_entity(self) -> Permission:
        return Permission(id=self.id, module=self.module, action=self.action, description=self.description)


class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    permissions = relationship("PermissionModel", secondary=role_permissions_table, lazy="joined")

    def to_entity(self) -> Role:
        return Role(
            id=self.id, name=self.name, description=self.description,
            active=self.active, created_at=self.created_at,
        )
```

- [ ] **Step 2: Update UserModel**

Replace the full contents of `backend/infra/models/user_model.py`:

```python
from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from backend.infra.models import Base
from backend.domain.entities.user import User
import uuid


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    email = Column(Text, nullable=False, unique=True)
    username = Column(Text, nullable=False, unique=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    password_hash = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    google_sub = Column(Text, nullable=True, unique=True)
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    role = relationship("RoleModel", lazy="joined")

    __table_args__ = (
        CheckConstraint("email LIKE '%@sywork.net'", name="ck_users_email_domain"),
    )

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            username=self.username,
            role=self.role.to_entity(),
            active=self.active,
            google_sub=self.google_sub,
            password_hash=self.password_hash,
            last_login_at=self.last_login_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            role_id=user.role.id,
            password_hash=user.password_hash,
            active=user.active,
            google_sub=user.google_sub,
        )
```

- [ ] **Step 3: Register the new models so Alembic autodiscovers them**

Modify `backend/infra/models/__init__.py` — add the role/permission import before the `UserModel` import (dependency order):

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from backend.infra.models.role_model import RoleModel, PermissionModel  # noqa: E402, F401
from backend.infra.models.user_model import UserModel  # noqa: E402, F401
from backend.infra.models.client_model import ClientModel  # noqa: E402, F401
from backend.infra.models.project_model import ProjectModel  # noqa: E402, F401
from backend.infra.models.resource_model import SkillModel, ResourceModel  # noqa: E402, F401
```

- [ ] **Step 4: Byte-compile**

Run: `docker exec sywork_backend python -m py_compile backend/infra/models/role_model.py backend/infra/models/user_model.py backend/infra/models/__init__.py`
Expected: no output (success)

- [ ] **Step 5: Commit**

```bash
git add backend/infra/models/role_model.py backend/infra/models/user_model.py backend/infra/models/__init__.py
git commit -m "feat(infra): add RoleModel/PermissionModel, migrate UserModel to role_id FK"
```

---

### Task 6: Repositories — RoleRepository, PermissionRepository, UserRepository updates

**Files:**
- Create: `backend/infra/repositories/role_repo.py`
- Modify: `backend/infra/repositories/user_repo.py`

**Interfaces:**
- Consumes: `RoleModel`, `PermissionModel`, `role_permissions_table` (Task 5), `Role`/`Permission` (Task 1).
- Produces:
  - `RoleRepository`: `get_by_id(role_id)`, `get_by_name(name)`, `list_paginated(page, page_size, active=None)`, `list_permissions_for_role(role_id) -> list[Permission]`, `create(role: Role) -> Role`, `update(role: Role) -> Role`, `set_active(role_id, active) -> Optional[Role]`, `replace_permissions(role_id, permission_ids: list[uuid.UUID]) -> Optional[Role]`, `count_active_users_with_role(role_id) -> int`, `count_roles_with_permission(permission_id) -> int`.
  - `PermissionRepository`: `list_all() -> list[Permission]`, `get_by_id(permission_id)`, `get_by_module_action(module, action)`, `create(permission: Permission) -> Permission`, `delete(permission_id) -> bool`.
  - `UserRepository.get_by_username_or_email(identifier: str) -> Optional[User]` (new), `UserRepository.update_role(user_id, role_id: uuid.UUID) -> Optional[User]` (signature changed from `role: Role` to `role_id: uuid.UUID`), `UserRepository.count_active_admins()` (rewritten to join `roles`).

- [ ] **Step 1: Create RoleRepository and PermissionRepository**

Create `backend/infra/repositories/role_repo.py`:

```python
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.infra.models.role_model import RoleModel, PermissionModel, role_permissions_table
from backend.infra.models.user_model import UserModel
from backend.domain.entities.role import Role, Permission


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        model = self._db.get(RoleModel, role_id)
        return model.to_entity() if model else None

    def get_by_name(self, name: str) -> Optional[Role]:
        model = self._db.query(RoleModel).filter(RoleModel.name == name).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, active: bool | None = None) -> tuple[list[Role], int]:
        q = self._db.query(RoleModel)
        if active is not None:
            q = q.filter(RoleModel.active == active)
        total = q.count()
        models = q.order_by(RoleModel.name).offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def list_permissions_for_role(self, role_id: uuid.UUID) -> list[Permission]:
        model = self._db.get(RoleModel, role_id)
        return [p.to_entity() for p in (model.permissions if model else [])]

    def create(self, role: Role) -> Role:
        model = RoleModel(id=role.id, name=role.name, description=role.description, active=role.active)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update(self, role: Role) -> Role:
        model = self._db.get(RoleModel, role.id)
        if not model:
            return role
        model.name = role.name
        model.description = role.description
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def set_active(self, role_id: uuid.UUID, active: bool) -> Optional[Role]:
        model = self._db.get(RoleModel, role_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def replace_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> Optional[Role]:
        model = self._db.get(RoleModel, role_id)
        if not model:
            return None
        model.permissions = [p for p in (self._db.get(PermissionModel, pid) for pid in permission_ids) if p]
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def count_active_users_with_role(self, role_id: uuid.UUID) -> int:
        return self._db.query(UserModel).filter(UserModel.role_id == role_id, UserModel.active == True).count()

    def count_roles_with_permission(self, permission_id: uuid.UUID) -> int:
        return (
            self._db.query(role_permissions_table)
            .filter(role_permissions_table.c.permission_id == permission_id)
            .count()
        )


class PermissionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Permission]:
        models = self._db.query(PermissionModel).order_by(PermissionModel.module, PermissionModel.action).all()
        return [m.to_entity() for m in models]

    def get_by_id(self, permission_id: uuid.UUID) -> Optional[Permission]:
        model = self._db.get(PermissionModel, permission_id)
        return model.to_entity() if model else None

    def get_by_module_action(self, module: str, action: str) -> Optional[Permission]:
        model = self._db.query(PermissionModel).filter(
            PermissionModel.module == module, PermissionModel.action == action,
        ).first()
        return model.to_entity() if model else None

    def create(self, permission: Permission) -> Permission:
        model = PermissionModel(
            id=permission.id, module=permission.module, action=permission.action,
            description=permission.description,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def delete(self, permission_id: uuid.UUID) -> bool:
        model = self._db.get(PermissionModel, permission_id)
        if not model:
            return False
        self._db.delete(model)
        self._db.commit()
        return True
```

- [ ] **Step 2: Update UserRepository**

Replace the full contents of `backend/infra/repositories/user_repo.py`:

```python
from typing import Optional
from sqlalchemy.orm import Session
from backend.infra.models.user_model import UserModel
from backend.infra.models.role_model import RoleModel
from backend.domain.entities.user import User
import uuid


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        return model.to_entity() if model else None

    def get_by_email(self, email: str) -> Optional[User]:
        model = self._db.query(UserModel).filter(UserModel.email == email).first()
        return model.to_entity() if model else None

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        model = self._db.query(UserModel).filter(
            (UserModel.username == identifier) | (UserModel.email == identifier)
        ).first()
        return model.to_entity() if model else None

    def get_by_google_sub(self, google_sub: str) -> Optional[User]:
        model = self._db.query(UserModel).filter(UserModel.google_sub == google_sub).first()
        return model.to_entity() if model else None

    def list_paginated(self, page: int = 1, page_size: int = 20, role: Optional[str] = None, active: Optional[bool] = None) -> tuple[list[User], int]:
        q = self._db.query(UserModel)
        if role:
            q = q.join(RoleModel, UserModel.role_id == RoleModel.id).filter(RoleModel.name == role)
        if active is not None:
            q = q.filter(UserModel.active == active)
        total = q.count()
        models = q.offset((page - 1) * page_size).limit(page_size).all()
        return [m.to_entity() for m in models], total

    def create(self, user: User) -> User:
        model = UserModel.from_entity(user)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        if not model:
            return None
        model.role_id = role_id
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def set_active(self, user_id: uuid.UUID, active: bool) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        if not model:
            return None
        model.active = active
        self._db.commit()
        self._db.refresh(model)
        return model.to_entity()

    def update_last_login(self, user_id: uuid.UUID) -> None:
        from sqlalchemy.sql import func
        self._db.query(UserModel).filter(UserModel.id == user_id).update({"last_login_at": func.now()})
        self._db.commit()

    def count_active_admins(self) -> int:
        return (
            self._db.query(UserModel)
            .join(RoleModel, UserModel.role_id == RoleModel.id)
            .filter(RoleModel.name == "Admin", UserModel.active == True)
            .count()
        )
```

Note `list_paginated`'s `role` filter parameter now filters by role **name** (a join), not the old raw text column — its call site in `backend/api/routes/users.py::UserList.get` already passes a plain string through unchanged, so it doesn't need to change.

- [ ] **Step 3: Byte-compile**

Run: `docker exec sywork_backend python -m py_compile backend/infra/repositories/role_repo.py backend/infra/repositories/user_repo.py`
Expected: no output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/infra/repositories/role_repo.py backend/infra/repositories/user_repo.py
git commit -m "feat(infra): add RoleRepository/PermissionRepository, update UserRepository for role_id"
```

---

### Task 7: Fix every remaining Role-enum reference (middleware, users route, auth route, conftest)

**Files:**
- Modify: `backend/api/middleware/auth.py`
- Modify: `backend/api/middleware/rbac.py`
- Modify: `backend/api/routes/users.py`
- Modify: `backend/api/routes/auth.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/api/test_users_api.py`

**Interfaces:**
- Consumes: `Role` (Task 1), `RoleRepository`/`PermissionRepository`/`UserRepository.get_by_username_or_email` (Task 6), `RoleService`/`RoleBusinessError` (Task 4), `AuthService` (Task 2).
- Produces: `_user_to_dict` returns `"role": {"id": ..., "name": ...}`; `PATCH /api/users/{id}/role` expects `{"role_id": "<uuid>"}`; `POST /api/auth/login` (new); `GET /api/auth/me` returns the enriched `{role, permissions}` shape; `resolver_user` test fixture builds a real DB-backed user with a real `Role`.

This is the task that makes the whole import chain consistent again — it is intentionally the largest task in this plan. Do not skip any file; a single missed import breaks `pytest` collection for the entire suite (see Critical Sequencing Note at the top of this document).

- [ ] **Step 1: Fix the dev-bypass fake user in auth middleware**

In `backend/api/middleware/auth.py`, change the top-level import from:
```python
from backend.domain.entities.user import User, Role
```
to:
```python
from backend.domain.entities.user import User
```

Then replace the `_set_dev_user` function:

```python
def _set_dev_user():
    """Injects a fake admin user into g so endpoint code works normally."""
    import uuid as _uuid
    from datetime import datetime
    from backend.domain.entities.role import Role

    if not hasattr(g, "current_user"):
        g.current_user = User(
            id=_uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="dev@sywork.net",
            username="dev",
            role=Role(id=_uuid.UUID("00000000-0000-0000-0000-000000000002"), name="Admin"),
            active=True,
            created_at=datetime.utcnow(),
        )
```

- [ ] **Step 2: Fix rbac.py**

Replace the full contents of `backend/api/middleware/rbac.py`:

```python
from functools import wraps
from flask import g, jsonify
from backend.api.middleware.auth import jwt_required_active


def require_role(*role_names: str):
    """Decorator: require JWT (active user) + one of the given role names."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required_active
        def wrapper(*args, **kwargs):
            user = g.current_user
            if user.role.name not in role_names:
                return jsonify({"error": "forbidden", "message": "Acceso denegado"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 3: Rewrite users.py for the dynamic role shape**

Replace the full contents of `backend/api/routes/users.py`:

```python
from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.services.role_service import RoleService, RoleBusinessError
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("users", description="Gestión de usuarios y roles del sistema", path="/api/users")
_svc = RoleService()

_error = error_model(ns, "UserError")

_role_ref = ns.model("UserRoleRef", {
    "id": fields.String(description="UUID del rol"),
    "name": fields.String(description="Nombre del rol"),
})

_user_out = ns.model("User", {
    "id": fields.String(description="UUID del usuario"),
    "email": fields.String(description="Email corporativo (@sywork.net)"),
    "username": fields.String(description="Nombre de usuario"),
    "role": fields.Nested(_role_ref, description="Rol del sistema"),
    "active": fields.Boolean(description="Estado activo"),
    "last_login_at": fields.String(description="Último login ISO-8601 (null si nunca ha ingresado)"),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_user_list_out = ns.model("UserList", {
    "items": fields.List(fields.Nested(_user_out)),
    "total": fields.Integer(description="Total de usuarios"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_role_input = ns.model("RoleIdInput", {
    "role_id": fields.String(required=True, description="UUID del rol a asignar"),
})

_status_result = ns.model("UserStatusResult", {
    "id": fields.String(description="UUID del usuario"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})


def _user_to_dict(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": {"id": str(user.role.id), "name": user.role.name},
        "active": user.active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ── Resources ────────────────────────────────────────────────────────────────

@ns.route("")
class UserList(Resource):
    @ns.doc(
        "list_users",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "role": {"description": "Filtrar por nombre de rol", "type": "string"},
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(200, "Listado de usuarios del sistema", _user_list_out)
    @ns.response(400, "Parámetros inválidos", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar usuarios del sistema con filtros por rol y estado"""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        role_filter = request.args.get("role")
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        try:
            db = next(get_db())
            users, total = UserRepository(db).list_paginated(page=page, page_size=page_size, role=role_filter, active=active)
            return {"items": [_user_to_dict(u) for u in users], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()


@ns.route("/<string:user_id>")
@ns.param("user_id", "UUID del usuario")
class UserDetail(Resource):
    @ns.doc("get_user")
    @ns.response(200, "Detalle del usuario", _user_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, user_id: str):
        """Obtener detalle de un usuario por ID"""
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = next(get_db())
            user = UserRepository(db).get_by_id(uid)
            if not user:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return _user_to_dict(user), 200
        except Exception:
            return server_error()


@ns.route("/<string:user_id>/role")
@ns.param("user_id", "UUID del usuario")
class UserRole(Resource):
    @ns.doc("change_role")
    @ns.expect(_role_input, validate=False)
    @ns.response(200, "Rol actualizado correctamente", _user_out)
    @ns.response(400, "UUID inválido o role_id faltante", _error)
    @ns.response(404, "Usuario o rol no encontrado", _error)
    @ns.response(409, "Conflicto de negocio (ej: ultimo admin activo)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Cambiar el rol de un usuario. No se puede degradar al ultimo administrador activo."""
        from flask import request
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        role_id = parse_uuid(data.get("role_id", ""))
        if not role_id:
            return {"error": "validation_error", "message": "El campo 'role_id' es requerido y debe ser un UUID"}, 400
        try:
            db = next(get_db())
            repo = UserRepository(db)
            role_repo = RoleRepository(db)
            new_role = role_repo.get_by_id(role_id)
            if not new_role:
                return {"error": "role_not_found", "message": "Rol no encontrado"}, 404
            _svc.validate_role_change(uid, new_role.name, users_repo=repo)
            updated = repo.update_role(uid, role_id)
            if not updated:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return _user_to_dict(updated), 200
        except RoleBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:user_id>/deactivate")
@ns.param("user_id", "UUID del usuario")
class UserDeactivate(Resource):
    @ns.doc("deactivate_user")
    @ns.response(200, "Usuario desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(409, "No se puede desactivar (ej: ultimo admin activo)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Desactivar un usuario. No se puede desactivar al ultimo administrador activo."""
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = next(get_db())
            repo = UserRepository(db)
            _svc.validate_deactivation(uid, users_repo=repo)
            updated = repo.set_active(uid, False)
            if not updated:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            return {"id": user_id, "active": False}, 200
        except RoleBusinessError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:user_id>/activate")
@ns.param("user_id", "UUID del usuario")
class UserActivate(Resource):
    @ns.doc("activate_user")
    @ns.response(200, "Usuario activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Usuario no encontrado", _error)
    @ns.response(409, "El usuario ya esta activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, user_id: str):
        """Activar un usuario previamente desactivado"""
        uid = parse_uuid(user_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de usuario invalido"}, 400
        try:
            db = next(get_db())
            repo = UserRepository(db)
            user = repo.get_by_id(uid)
            if not user:
                return {"error": "not_found", "message": "Usuario no encontrado"}, 404
            if user.active:
                return {"error": "already_active", "message": "El usuario ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": user_id, "active": True}, 200
        except Exception:
            return server_error()
```

This is a straight port of the existing file's structure (`UserList`, `UserDetail`, `UserRole`, `UserDeactivate`, `UserActivate`) with only `_user_to_dict` and `UserRole.patch` changed for the dynamic role shape — the other three classes are byte-for-byte what's already in the repo.

- [ ] **Step 4: Rewrite auth.py — add the provisional login endpoint**

Replace the full contents of `backend/api/routes/auth.py`:

```python
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ALLOWED_DOMAIN = "sywork.net"
_auth_svc = AuthService()


def _user_payload(user, db) -> dict:
    permissions = RoleRepository(db).list_permissions_for_role(user.role.id)
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": {"id": str(user.role.id), "name": user.role.name},
        "permissions": [{"module": p.module, "action": p.action} for p in permissions],
    }


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login provisional por usuario/contraseña. Coexiste con /google, no lo reemplaza."""
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username_or_email") or "").strip()
    password = data.get("password") or ""
    if not identifier or not password:
        return jsonify({"error": "validation_error", "message": "username_or_email y password son requeridos"}), 400

    db = next(get_db())
    repo = UserRepository(db)
    user = repo.get_by_username_or_email(identifier)
    if not user or not user.active or not _auth_svc.verify_password(password, user.password_hash):
        return jsonify({"error": "unauthorized", "message": "Usuario o contraseña incorrectos"}), 401

    repo.update_last_login(user.id)
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.name})
    payload = _user_payload(user, db)
    payload["access_token"] = token
    return jsonify(payload), 200


@auth_bp.route("/google", methods=["POST"])
def google_login():
    data = request.get_json(silent=True) or {}
    id_token_str = data.get("id_token")
    if not id_token_str:
        return jsonify({"error": "bad_request", "message": "id_token requerido"}), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            os.environ.get("GOOGLE_CLIENT_ID"),
        )
    except ValueError:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    email: str = idinfo.get("email", "")
    domain = email.split("@")[-1] if "@" in email else ""
    if domain != ALLOWED_DOMAIN:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    google_sub: str = idinfo["sub"]
    db = next(get_db())
    repo = UserRepository(db)

    user = repo.get_by_google_sub(google_sub) or repo.get_by_email(email)
    if user is None:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    if not user.active:
        return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401

    repo.update_last_login(user.id)
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.name})
    payload = _user_payload(user, db)
    payload["access_token"] = token
    return jsonify(payload), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    from backend.api.middleware.auth import jwt_required_active
    from flask import g

    @jwt_required_active
    def _inner():
        db = next(get_db())
        return jsonify(_user_payload(g.current_user, db)), 200

    return _inner()
```

- [ ] **Step 5: Fix conftest.py**

Replace the full contents of `backend/tests/conftest.py`:

```python
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
```

This drops the old `os.environ.setdefault("DEV_SKIP_AUTH", "true")` line — the login tests added in Task 8 need `/api/auth/me` to exercise the real JWT path, not the dev-bypass fake admin. The `RoleRepository` import inside `resolver_user` stays local (not top-level) so this file keeps importing cleanly regardless of task ordering elsewhere; it is only ever called by tests once the migration (Task 8, Step 5 below) has already run.

- [ ] **Step 6: Update test_users_api.py for the new role shape**

In `backend/tests/api/test_users_api.py`, replace `test_get_resolver_user`, `test_change_role`, and `test_change_role_invalid_value_returns_400`:

```python
def test_get_resolver_user(client, resolver_user):
    resp = client.get(f"/api/users/{resolver_user.id}")
    assert resp.status_code == 200
    assert resp.get_json()["role"]["name"] == "Resolutor"


def test_change_role(client, resolver_user):
    coordinador_role = next(
        r for r in client.get("/api/roles?page_size=100").get_json()["items"] if r["name"] == "Coordinador"
    )
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role_id": coordinador_role["id"]})
    assert resp.status_code == 200
    assert resp.get_json()["role"]["name"] == "Coordinador"


def test_change_role_invalid_uuid_returns_400(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role_id": "not-a-uuid"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_change_role_unknown_role_returns_404(client, resolver_user):
    resp = client.patch(f"/api/users/{resolver_user.id}/role", json={"role_id": "00000000-0000-0000-0000-000000000099"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "role_not_found"
```

Note `test_change_role` calls `GET /api/roles`, which doesn't exist until Task 9 — this specific test stays red until then. Every other test in this file only needs `resolver_user`, which is self-contained once Task 8's migration has run.

- [ ] **Step 7: Byte-compile everything touched in this task**

Run: `docker exec sywork_backend python -m py_compile backend/api/middleware/auth.py backend/api/middleware/rbac.py backend/api/routes/users.py backend/api/routes/auth.py backend/tests/conftest.py backend/tests/api/test_users_api.py`
Expected: no output (success)

- [ ] **Step 8: Verify the app boots**

Run: `docker exec sywork_backend python -c "from backend.app import create_app; create_app(); print('OK')"`
Expected: `OK`. If this fails, re-check every file changed in Tasks 1-7 for a stray `Role` import from `backend.domain.entities.user` — that is the only class of bug this step is designed to catch.

- [ ] **Step 9: Commit**

```bash
git add backend/api/middleware/auth.py backend/api/middleware/rbac.py backend/api/routes/users.py backend/api/routes/auth.py backend/tests/conftest.py backend/tests/api/test_users_api.py
git commit -m "fix(api): migrate middleware, users route, auth route, and test fixtures off the Role enum"
```

---

### Task 8: Alembic migration 009 — schema + seed data, then the first full test run

**Files:**
- Create: `backend/infra/migrations/versions/009_roles_permissions_login.py`

**Interfaces:**
- Consumes: nothing from Python code (migrations run raw SQL / SQLAlchemy Core, independent of the domain/infra layers — this is intentional, matches how `004_create_skills_resources.py` seeds data directly).
- Produces: `roles`, `permissions`, `role_permissions` tables; `users.role_id`/`username`/`password_hash` columns; the old `users.role` text column and its `ck_users_role` check constraint are dropped. Seeds 4 roles, 24 permissions (6 modules × 4 actions), the role→permission matrix, and 4 provisional-login users.

- [ ] **Step 1: Write the migration**

Create `backend/infra/migrations/versions/009_roles_permissions_login.py`:

```python
"""create roles, permissions, role_permissions; migrate users off fixed role enum; add username/password_hash; seed data

Revision ID: 009
Revises: 008
Create Date: 2026-07-01
"""
import secrets
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

MODULES = ["clients", "projects", "resources", "skills", "users", "roles"]
ACTIONS = ["view", "create", "edit", "deactivate"]

ROLE_PROFILES = {
    "Admin": {m: list(ACTIONS) for m in MODULES},
    "Coordinador": {
        "clients": list(ACTIONS), "projects": list(ACTIONS), "resources": list(ACTIONS),
        "skills": list(ACTIONS), "users": ["view"], "roles": [],
    },
    "QM": {
        "clients": list(ACTIONS), "projects": ["view"], "resources": list(ACTIONS),
        "skills": list(ACTIONS), "users": ["view"], "roles": [],
    },
    "Resolutor": {
        "clients": ["view"], "projects": ["view"], "resources": ["view"],
        "skills": ["view"], "users": ["view"], "roles": [],
    },
}

SEED_USERS = [
    ("admin@sywork.net", "admin", "Admin"),
    ("coordinador@sywork.net", "coordinador", "Coordinador"),
    ("qm@sywork.net", "qm", "QM"),
    ("resolutor@sywork.net", "resolutor", "Resolutor"),
]

OLD_ROLE_TO_NEW_NAME = {
    "admin": "Admin", "coordinator": "Coordinador", "qm": "QM", "resolver": "Resolutor",
}


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("module", "action", name="uq_permissions_module_action"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False, primary_key=True),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("permissions.id"), nullable=False, primary_key=True),
    )

    op.add_column("users", sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=True))
    op.add_column("users", sa.Column("username", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))

    # ── seed roles ──────────────────────────────────────────────────────
    role_ids = {}
    for name in ROLE_PROFILES:
        role_id = uuid.uuid4()
        role_ids[name] = role_id
        bind.execute(
            sa.text("INSERT INTO roles (id, name, description) VALUES (:id, :name, :description)"),
            {"id": str(role_id), "name": name, "description": f"Rol {name}"},
        )

    # ── seed permissions (6 modules x 4 actions = 24) ──────────────────
    permission_ids = {}
    for module in MODULES:
        for action in ACTIONS:
            perm_id = uuid.uuid4()
            permission_ids[(module, action)] = perm_id
            bind.execute(
                sa.text("INSERT INTO permissions (id, module, action) VALUES (:id, :module, :action)"),
                {"id": str(perm_id), "module": module, "action": action},
            )

    # ── seed role_permissions matrix ───────────────────────────────────
    for role_name, module_actions in ROLE_PROFILES.items():
        for module, actions in module_actions.items():
            for action in actions:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"
                    ),
                    {"role_id": str(role_ids[role_name]), "permission_id": str(permission_ids[(module, action)])},
                )

    # ── backfill existing users onto the new role_id/username columns ──
    existing_users = bind.execute(sa.text("SELECT id, email, role FROM users")).fetchall()
    for row in existing_users:
        new_role_name = OLD_ROLE_TO_NEW_NAME.get(row.role)
        if new_role_name is None:
            raise RuntimeError(f"Usuario {row.email} tiene un role desconocido: {row.role!r}")
        username = row.email.split("@")[0]
        bind.execute(
            sa.text("UPDATE users SET role_id = :role_id, username = :username WHERE id = :id"),
            {"role_id": str(role_ids[new_role_name]), "username": username, "id": str(row.id)},
        )

    # ── seed the 4 provisional-login users (one shared provisional password) ──
    provisional_password = secrets.token_urlsafe(9)
    password_hash = generate_password_hash(provisional_password)
    for email, username, role_name in SEED_USERS:
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, username, role_id, password_hash, active) "
                "VALUES (:id, :email, :username, :role_id, :password_hash, true) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()), "email": email, "username": username,
                "role_id": str(role_ids[role_name]), "password_hash": password_hash,
            },
        )

    print("=" * 70)
    print("PROVISIONAL LOGIN PASSWORD (shared by admin/coordinador/qm/resolutor):")
    print(f"    {provisional_password}")
    print("Guarda esta contraseña ahora - no se vuelve a mostrar ni se guarda en el repo.")
    print("=" * 70)

    # ── finalize users schema ──────────────────────────────────────────
    op.alter_column("users", "role_id", nullable=False)
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column("users", sa.Column("role", sa.Text(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE users u SET role = CASE r.name
            WHEN 'Admin' THEN 'admin'
            WHEN 'Coordinador' THEN 'coordinator'
            WHEN 'QM' THEN 'qm'
            WHEN 'Resolutor' THEN 'resolver'
        END
        FROM roles r WHERE u.role_id = r.id
    """))
    op.alter_column("users", "role", nullable=False, server_default="resolver")
    op.create_check_constraint("ck_users_role", "users", "role IN ('admin','coordinator','qm','resolver')")
    seed_emails = ",".join(f"'{email}'" for email, _, _ in SEED_USERS)
    op.execute(f"DELETE FROM users WHERE email IN ({seed_emails})")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
    op.drop_column("users", "role_id")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
```

- [ ] **Step 2: Byte-compile the migration**

Run: `docker exec sywork_backend python -m py_compile backend/infra/migrations/versions/009_roles_permissions_login.py`
Expected: no output (success)

- [ ] **Step 3: Apply the migration**

Run: `docker exec sywork_backend alembic upgrade head`
Expected: alembic log lines ending in `Running upgrade 008 -> 009`, then the printed `PROVISIONAL LOGIN PASSWORD` block with a real generated password. **Copy that password down now** — it will not be shown again and must not be committed anywhere.

- [ ] **Step 4: Verify the schema and seed data landed correctly**

Run:
```bash
docker exec sywork_backend python -c "
from backend.infra.database import get_db
from sqlalchemy import text
db = next(get_db())
print('roles:', db.execute(text('SELECT count(*) FROM roles')).scalar())
print('permissions:', db.execute(text('SELECT count(*) FROM permissions')).scalar())
print('role_permissions:', db.execute(text('SELECT count(*) FROM role_permissions')).scalar())
print('seed users:', db.execute(text(\"SELECT email, username FROM users WHERE email LIKE '%@sywork.net' AND username IN ('admin','coordinador','qm','resolutor') ORDER BY email\")).fetchall())
"
```
Expected: `roles: 4`, `permissions: 24`, `role_permissions: 60` (Admin 24 + Coordinador 17 + QM 14 + Resolutor 5), and the 4 seed emails/usernames listed.

- [ ] **Step 5: Run the FULL test suite for the first time**

This is the first `pytest` invocation since Task 1 started (see the Critical Sequencing Note at the top of this document). Every domain test written in Tasks 1-4, plus the `test_users_api.py` fixes from Task 7, should now pass — the import chain is consistent and the DB has the seed data those tests depend on.

Run: `docker exec sywork_backend python -m pytest tests/domain/ tests/api/test_users_api.py tests/api/test_clients_api.py tests/api/test_projects_api.py tests/api/test_resources_and_skills_api.py tests/api/test_health_api.py -v`
Expected: all tests PASS except `tests/api/test_users_api.py::test_change_role` (still needs `GET /api/roles`, built in Task 9 — confirm this is the *only* failure). If anything else fails, stop and fix it before proceeding — Task 9 onward assumes this baseline is green.

- [ ] **Step 6: Commit**

```bash
git add backend/infra/migrations/versions/009_roles_permissions_login.py
git commit -m "feat(db): migrate users off fixed role enum, add roles/permissions tables, seed data"
```

---

### Task 9: Roles API routes

**Files:**
- Create: `backend/api/routes/roles.py`
- Modify: `backend/app.py`
- Test: `backend/tests/api/test_roles_api.py`

**Interfaces:**
- Consumes: `RoleRepository` (Task 6), `RoleAdminService`/`RoleAdminError` (Task 3), `parse_uuid`/`error_model`/`server_error` (existing `backend/api/routes/_shared.py`).
- Produces: `GET/POST /api/roles`, `GET/PATCH /api/roles/{id}`, `PATCH /api/roles/{id}/deactivate`, `PATCH /api/roles/{id}/activate`, `PUT /api/roles/{id}/permissions`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/api/test_roles_api.py`:

```python
def test_list_roles_includes_the_4_seed_roles(client):
    resp = client.get("/api/roles?page_size=100")
    assert resp.status_code == 200
    names = {r["name"] for r in resp.get_json()["items"]}
    assert {"Admin", "Coordinador", "QM", "Resolutor"}.issubset(names)


def test_create_role_returns_201_with_location(client, unique_name):
    resp = client.post("/api/roles", json={"name": f"Role-{unique_name}", "description": "test role"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/roles/{body['id']}"
    assert body["permissions"] == []


def test_duplicate_role_name_returns_409(client, unique_name):
    name = f"Role-{unique_name}"
    client.post("/api/roles", json={"name": name})
    dup = client.post("/api/roles", json={"name": name})
    assert dup.status_code == 409


def test_replace_role_permissions(client, unique_name):
    role = client.post("/api/roles", json={"name": f"Role-{unique_name}"}).get_json()
    perms = client.get("/api/permissions").get_json()["items"]
    clients_view = next(p["id"] for p in perms if p["module"] == "clients" and p["action"] == "view")

    resp = client.put(f"/api/roles/{role['id']}/permissions", json={"permission_ids": [clients_view]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["permissions"]) == 1
    assert body["permissions"][0]["module"] == "clients"
    assert body["permissions"][0]["action"] == "view"


def test_cannot_deactivate_admin_role(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    admin_role = next(r for r in roles if r["name"] == "Admin")
    resp = client.patch(f"/api/roles/{admin_role['id']}/deactivate")
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "cannot_deactivate_admin_role"


def test_deactivate_role_with_active_users_returns_409_with_count(client):
    roles = client.get("/api/roles?page_size=100").get_json()["items"]
    coordinador_role = next(r for r in roles if r["name"] == "Coordinador")
    resp = client.patch(f"/api/roles/{coordinador_role['id']}/deactivate")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "role_in_use"
    assert body["active_users_count"] >= 1


def test_deactivate_then_activate_role_with_no_users_roundtrip(client, unique_name):
    role = client.post("/api/roles", json={"name": f"Role-{unique_name}"}).get_json()
    rid = role["id"]

    deactivated = client.patch(f"/api/roles/{rid}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.get_json() == {"id": rid, "active": False}

    activated = client.patch(f"/api/roles/{rid}/activate")
    assert activated.status_code == 200
    assert activated.get_json() == {"id": rid, "active": True}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker exec sywork_backend python -m pytest tests/api/test_roles_api.py -v`
Expected: FAIL — `404` on every request (no `/api/roles` route registered yet).

- [ ] **Step 3: Implement the roles route**

Create `backend/api/routes/roles.py`:

```python
from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.role_repo import RoleRepository
from backend.infra.database import get_db
from backend.domain.entities.role import Role
from backend.domain.services.role_admin_service import RoleAdminService, RoleAdminError
from backend.api.routes._shared import parse_uuid, error_model, server_error

ns = Namespace("roles", description="Gestión de roles y sus permisos", path="/api/roles")
_svc = RoleAdminService()

_error = error_model(ns, "RoleError")

_permission_ref = ns.model("RolePermissionRef", {
    "id": fields.String(description="UUID del permiso"),
    "module": fields.String(description="Módulo"),
    "action": fields.String(description="Acción"),
})

_role_out = ns.model("Role", {
    "id": fields.String(description="UUID del rol"),
    "name": fields.String(description="Nombre del rol"),
    "description": fields.String(description="Descripción"),
    "active": fields.Boolean(description="Estado activo"),
    "permissions": fields.List(fields.Nested(_permission_ref)),
    "created_at": fields.String(description="Fecha de creación ISO-8601"),
})

_role_list_out = ns.model("RoleList", {
    "items": fields.List(fields.Nested(_role_out)),
    "total": fields.Integer(description="Total de roles"),
    "page": fields.Integer(description="Página actual"),
    "page_size": fields.Integer(description="Tamaño de página"),
})

_role_input = ns.model("RoleInput", {
    "name": fields.String(required=True, description="Nombre del rol", example="Auditor"),
    "description": fields.String(description="Descripción del rol"),
})

_role_update = ns.model("RoleUpdate", {
    "name": fields.String(description="Nuevo nombre"),
    "description": fields.String(description="Nueva descripción"),
})

_permissions_update = ns.model("RolePermissionsUpdate", {
    "permission_ids": fields.List(fields.String, required=True, description="Lista completa de UUIDs de permisos (reemplaza los actuales)"),
})

_status_result = ns.model("RoleStatusResult", {
    "id": fields.String(description="UUID del rol"),
    "active": fields.Boolean(description="Nuevo estado activo"),
})


def _role_to_dict(role, repo: RoleRepository) -> dict:
    perms = repo.list_permissions_for_role(role.id)
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "active": role.active,
        "permissions": [{"id": str(p.id), "module": p.module, "action": p.action} for p in perms],
        "created_at": role.created_at.isoformat() if role.created_at else None,
    }


@ns.route("")
class RoleList(Resource):
    @ns.doc(
        "list_roles",
        params={
            "page": {"description": "Número de página (default: 1)", "type": "integer", "default": 1},
            "page_size": {"description": "Registros por página, máx 100 (default: 20)", "type": "integer", "default": 20},
            "active": {"description": "Filtrar por estado (true/false)", "type": "boolean"},
        },
    )
    @ns.response(200, "Listado de roles con sus permisos", _role_list_out)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar roles con sus permisos asignados"""
        from flask import request
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
        except ValueError:
            return {"error": "validation_error", "message": "page y page_size deben ser enteros"}, 400
        active_param = request.args.get("active")
        active = None if active_param is None else active_param.lower() == "true"
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            items, total = repo.list_paginated(page=page, page_size=page_size, active=active)
            return {"items": [_role_to_dict(r, repo) for r in items], "total": total, "page": page, "page_size": page_size}, 200
        except Exception:
            return server_error()

    @ns.doc("create_role")
    @ns.expect(_role_input, validate=False)
    @ns.response(201, "Rol creado", _role_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(409, "Nombre de rol duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear un nuevo rol (sin permisos asignados; usar PUT .../permissions después)"""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        name = data.get("name", "").strip()
        if not name:
            return {"error": "validation_error", "message": "El campo 'name' es requerido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            if repo.get_by_name(name):
                return {"error": "name_duplicate", "message": f"Ya existe un rol con el nombre {name}"}, 409
            role = Role.create(name=name, description=data.get("description"))
            created = repo.create(role)
            return _role_to_dict(created, repo), 201, {"Location": f"/api/roles/{created.id}"}
        except Exception:
            return server_error()


@ns.route("/<string:role_id>")
@ns.param("role_id", "UUID del rol")
class RoleDetail(Resource):
    @ns.doc("get_role")
    @ns.response(200, "Detalle del rol", _role_out)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self, role_id: str):
        """Obtener detalle de un rol incluyendo sus permisos"""
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            return _role_to_dict(role, repo), 200
        except Exception:
            return server_error()

    @ns.doc("update_role")
    @ns.expect(_role_update, validate=False)
    @ns.response(200, "Rol actualizado", _role_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "Nombre de rol duplicado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, role_id: str):
        """Actualizar nombre/descripción de un rol"""
        from flask import request
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            if "name" in data:
                new_name = str(data["name"]).strip()
                if not new_name:
                    return {"error": "validation_error", "message": "El nombre no puede estar vacio"}, 400
                existing = repo.get_by_name(new_name)
                if existing and existing.id != role.id:
                    return {"error": "name_duplicate", "message": f"Ya existe un rol con el nombre {new_name}"}, 409
                role.name = new_name
            if "description" in data:
                role.description = data["description"]
            updated = repo.update(role)
            return _role_to_dict(updated, repo), 200
        except Exception:
            return server_error()


@ns.route("/<string:role_id>/permissions")
@ns.param("role_id", "UUID del rol")
class RolePermissions(Resource):
    @ns.doc("replace_role_permissions")
    @ns.expect(_permissions_update, validate=False)
    @ns.response(200, "Permisos actualizados (reemplaza lista completa)", _role_out)
    @ns.response(400, "UUID inválido o cuerpo incorrecto", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def put(self, role_id: str):
        """Reemplazar todos los permisos de un rol (operación de reemplazo total, no incremental)"""
        from flask import request
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        data = request.get_json(silent=True) or {}
        permission_ids = [parse_uuid(pid) for pid in data.get("permission_ids", [])]
        permission_ids = [p for p in permission_ids if p]
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.replace_permissions(uid, permission_ids)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            return _role_to_dict(role, repo), 200
        except Exception:
            return server_error()


@ns.route("/<string:role_id>/deactivate")
@ns.param("role_id", "UUID del rol")
class RoleDeactivate(Resource):
    @ns.doc("deactivate_role")
    @ns.response(200, "Rol desactivado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "No se puede desactivar (rol Admin o con usuarios activos)", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, role_id: str):
        """Desactivar un rol. Bloqueado para el rol Admin y para roles con usuarios activos asignados."""
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            if not role.active:
                return {"error": "already_inactive", "message": "El rol ya esta inactivo"}, 409
            _svc.validate_deactivation(role, users_repo=repo)
            repo.set_active(uid, False)
            return {"id": role_id, "active": False}, 200
        except RoleAdminError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()


@ns.route("/<string:role_id>/activate")
@ns.param("role_id", "UUID del rol")
class RoleActivate(Resource):
    @ns.doc("activate_role")
    @ns.response(200, "Rol activado", _status_result)
    @ns.response(400, "UUID inválido", _error)
    @ns.response(404, "Rol no encontrado", _error)
    @ns.response(409, "El rol ya esta activo", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def patch(self, role_id: str):
        """Activar un rol previamente desactivado"""
        uid = parse_uuid(role_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de rol invalido"}, 400
        try:
            db = next(get_db())
            repo = RoleRepository(db)
            role = repo.get_by_id(uid)
            if not role:
                return {"error": "not_found", "message": "Rol no encontrado"}, 404
            if role.active:
                return {"error": "already_active", "message": "El rol ya esta activo"}, 409
            repo.set_active(uid, True)
            return {"id": role_id, "active": True}, 200
        except Exception:
            return server_error()
```

- [ ] **Step 4: Register the namespace**

In `backend/app.py`, add the import and registration alongside the existing maestros:

```python
    from backend.api.routes.clients import ns as ns_clients
    from backend.api.routes.projects import ns as ns_projects
    from backend.api.routes.resources import ns as ns_resources
    from backend.api.routes.users import ns as ns_users
    from backend.api.routes.roles import ns as ns_roles

    api.add_namespace(ns_clients)
    api.add_namespace(ns_projects)
    api.add_namespace(ns_resources)
    api.add_namespace(ns_users)
    api.add_namespace(ns_roles)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker exec sywork_backend python -m pytest tests/api/test_roles_api.py -v`
Expected: PASS (7 tests). If `test_deactivate_role_with_active_users_returns_409_with_count` fails because the count is 0, re-check that Task 8's migration ran (Step 3) before this task.

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes/roles.py backend/app.py backend/tests/api/test_roles_api.py
git commit -m "feat(api): add roles CRUD + permission assignment endpoint"
```

---

### Task 10: Permissions API routes

> **Plan amendment (post-Task-9 fix):** Task 9's own test needed `GET /api/permissions` to exist before this task ran, so that endpoint (and its own `backend/api/routes/permissions.py` file, `ns_permissions` namespace, and `app.py` registration) was pulled forward and already exists on `HEAD` before this task starts. This task now **extends** that existing file — it does not create it or re-register its namespace. Do not recreate `_error`, `_permission_out`, `_permission_list_out`, `_permission_to_dict`, or `PermissionList.get` — they already exist; adding them again would duplicate a Swagger model name and break `create_app()`.

**Files:**
- Modify: `backend/api/routes/permissions.py` (already exists — add `_permission_input` model, `PermissionList.post`, and a new `PermissionDetail` class)
- Test: `backend/tests/api/test_permissions_api.py`

**Interfaces:**
- Consumes: `PermissionRepository`, `RoleRepository` (Task 6), `RoleAdminService.validate_permission_delete` (Task 3) — all already imported in the existing file.
- Produces: `POST /api/permissions`, `DELETE /api/permissions/{id}` (the file's `GET /api/permissions` already exists from Task 9's fix).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/api/test_permissions_api.py`:

```python
def test_list_permissions_includes_the_24_seed_permissions(client):
    resp = client.get("/api/permissions")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] >= 24
    modules = {p["module"] for p in body["items"]}
    assert {"clients", "projects", "resources", "skills", "users", "roles"}.issubset(modules)


def test_create_permission_returns_201_with_location(client, unique_name):
    resp = client.post("/api/permissions", json={"module": f"mod_{unique_name}", "action": "view"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert resp.headers["Location"] == f"/api/permissions/{body['id']}"


def test_duplicate_module_action_returns_409(client, unique_name):
    payload = {"module": f"mod_{unique_name}", "action": "view"}
    client.post("/api/permissions", json=payload)
    dup = client.post("/api/permissions", json=payload)
    assert dup.status_code == 409
    assert dup.get_json()["error"] == "module_action_duplicate"


def test_delete_unused_permission(client, unique_name):
    created = client.post("/api/permissions", json={"module": f"mod_{unique_name}", "action": "edit"}).get_json()
    resp = client.delete(f"/api/permissions/{created['id']}")
    assert resp.status_code == 204


def test_delete_permission_assigned_to_a_role_returns_409(client, unique_name):
    permission = client.post("/api/permissions", json={"module": f"mod_{unique_name}", "action": "create"}).get_json()
    role = client.post("/api/roles", json={"name": f"Role-{unique_name}"}).get_json()
    client.put(f"/api/roles/{role['id']}/permissions", json={"permission_ids": [permission["id"]]})

    resp = client.delete(f"/api/permissions/{permission['id']}")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "permission_in_use"
    assert body["role_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker exec wt_sywork_backend python -m pytest tests/api/test_permissions_api.py -v`
Expected: `test_list_permissions_includes_the_24_seed_permissions` already PASSES (the GET endpoint exists from Task 9's fix). The other four tests (`test_create_permission_returns_201_with_location`, `test_duplicate_module_action_returns_409`, `test_delete_unused_permission`, `test_delete_permission_assigned_to_a_role_returns_409`) FAIL — `POST`/`DELETE` don't exist yet. This mixed result (1 pass, 4 fail) is the correct starting point for this task, not a red flag.

- [ ] **Step 3: Extend the permissions route with create/delete**

Open the existing `backend/api/routes/permissions.py` (created by Task 9's fix — do not overwrite the file; add to it). Its current contents are:

```python
from flask_restx import Namespace, Resource, fields
from backend.infra.repositories.role_repo import PermissionRepository
from backend.infra.database import get_db
from backend.api.routes._shared import error_model, server_error

ns = Namespace("permissions", description="Catálogo de permisos (módulo + acción)", path="/api/permissions")

_error = error_model(ns, "PermissionError")

_permission_out = ns.model("Permission", {
    "id": fields.String(description="UUID del permiso"),
    "module": fields.String(description="Módulo", example="clients"),
    "action": fields.String(description="Acción", example="view"),
    "description": fields.String(description="Descripción"),
})

_permission_list_out = ns.model("PermissionList", {
    "items": fields.List(fields.Nested(_permission_out)),
    "total": fields.Integer(description="Total de permisos"),
})


def _permission_to_dict(permission) -> dict:
    return {
        "id": str(permission.id), "module": permission.module,
        "action": permission.action, "description": permission.description,
    }


@ns.route("")
class PermissionList(Resource):
    @ns.doc("list_permissions")
    @ns.response(200, "Catálogo completo de permisos", _permission_list_out)
    @ns.response(500, "Error interno del servidor", _error)
    def get(self):
        """Listar el catálogo completo de permisos (módulo + acción)"""
        try:
            db = next(get_db())
            items = PermissionRepository(db).list_all()
            return {"items": [_permission_to_dict(p) for p in items], "total": len(items)}, 200
        except Exception:
            return server_error()
```

(If what you find on disk differs meaningfully from this, stop and report NEEDS_CONTEXT rather than guessing — the fix commit message is `fix(api): extract permissions namespace from roles.py into its own file, unblocking Task 10`, `git log --oneline -- backend/api/routes/permissions.py` will show it.)

Make these changes to this file:

1. Add two imports: `RoleRepository` (alongside the existing `PermissionRepository` import) and `Permission` from `backend.domain.entities.role`, and `RoleAdminService, RoleAdminError` from `backend.domain.services.role_admin_service`, and `parse_uuid` from `backend.api.routes._shared` (alongside the existing `error_model, server_error`):

```python
from backend.infra.repositories.role_repo import RoleRepository, PermissionRepository
from backend.domain.entities.role import Permission
from backend.domain.services.role_admin_service import RoleAdminService, RoleAdminError
from backend.api.routes._shared import parse_uuid, error_model, server_error
```

2. Add `_svc = RoleAdminService()` near the top, after the `ns = Namespace(...)` line.

3. Add the `_permission_input` model after `_permission_list_out`:

```python
_permission_input = ns.model("PermissionInput", {
    "module": fields.String(required=True, description="Módulo", example="clients"),
    "action": fields.String(required=True, description="Acción", example="view"),
    "description": fields.String(description="Descripción"),
})
```

4. Add a `post` method to the existing `PermissionList` class (alongside its existing `get`):

```python
    @ns.doc("create_permission")
    @ns.expect(_permission_input, validate=False)
    @ns.response(201, "Permiso creado", _permission_out)
    @ns.response(400, "Datos inválidos", _error)
    @ns.response(409, "Combinación módulo+acción duplicada", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def post(self):
        """Crear una definición de permiso nueva (módulo + acción)"""
        from flask import request
        data = request.get_json(silent=True)
        if not data:
            return {"error": "validation_error", "message": "El cuerpo debe ser JSON"}, 400
        module = data.get("module", "").strip()
        action = data.get("action", "").strip()
        if not module:
            return {"error": "validation_error", "message": "El campo 'module' es requerido"}, 400
        if not action:
            return {"error": "validation_error", "message": "El campo 'action' es requerido"}, 400
        try:
            db = next(get_db())
            repo = PermissionRepository(db)
            if repo.get_by_module_action(module, action):
                return {"error": "module_action_duplicate", "message": f"Ya existe el permiso {module}.{action}"}, 409
            permission = Permission.create(module=module, action=action, description=data.get("description"))
            created = repo.create(permission)
            return _permission_to_dict(created), 201, {"Location": f"/api/permissions/{created.id}"}
        except Exception:
            return server_error()
```

5. Add a new `PermissionDetail` class at the end of the file:

```python
@ns.route("/<string:permission_id>")
@ns.param("permission_id", "UUID del permiso")
class PermissionDetail(Resource):
    @ns.doc("delete_permission")
    @ns.response(204, "Permiso eliminado correctamente")
    @ns.response(400, "UUID inválido", _error)
    @ns.response(409, "No se puede eliminar: permiso asignado a algún rol", _error)
    @ns.response(500, "Error interno del servidor", _error)
    def delete(self, permission_id: str):
        """Eliminar una definición de permiso. Retorna 409 si está asignado a algún rol."""
        uid = parse_uuid(permission_id)
        if not uid:
            return {"error": "validation_error", "message": "ID de permiso invalido"}, 400
        try:
            db = next(get_db())
            perm_repo = PermissionRepository(db)
            role_repo = RoleRepository(db)
            _svc.validate_permission_delete(uid, roles_repo=role_repo)
            perm_repo.delete(uid)
            return "", 204
        except RoleAdminError as e:
            return {"error": e.code, "message": e.message, **e.extra}, e.status_code
        except Exception:
            return server_error()
```

- [ ] **Step 4: Confirm the namespace registration (no change needed)**

`backend/app.py` already imports and registers `ns_permissions` (from Task 9's fix). Open it and confirm these two lines are present — do not add them again, and do not touch `app.py` at all in this task unless they are somehow missing:

```python
    from backend.api.routes.permissions import ns as ns_permissions
    ...
    api.add_namespace(ns_permissions)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker exec sywork_backend python -m pytest tests/api/test_permissions_api.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes/permissions.py backend/app.py backend/tests/api/test_permissions_api.py
git commit -m "feat(api): add permissions catalog CRUD (list/create/delete)"
```

---

### Task 11: Provisional login endpoint tests

**Files:**
- Test: `backend/tests/api/test_auth_login_api.py`

**Interfaces:**
- Consumes: `AuthService` (Task 2), `RoleRepository` (Task 6), `UserRepository.get_by_username_or_email` (Task 6), `POST /api/auth/login` and `GET /api/auth/me` (already implemented in Task 7, Step 4 — this task only adds test coverage for them, since building the endpoint that early was necessary to unblock `create_app()`).

- [ ] **Step 1: Write the tests**

Create `backend/tests/api/test_auth_login_api.py`:

```python
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
```

- [ ] **Step 2: Run the tests**

Run: `docker exec sywork_backend python -m pytest tests/api/test_auth_login_api.py -v`
Expected: PASS (7 tests) — the endpoint itself was already built in Task 7 to unblock `create_app()`; this step should go green immediately with no implementation changes. If it doesn't, the bug is in Task 7's `auth.py`, not here.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/api/test_auth_login_api.py
git commit -m "test(api): add coverage for the provisional login endpoint"
```

---

### Task 12: Fix stale docs, full regression run, manual smoke test

**Files:**
- Modify: `backend/app.py` (Swagger description text only)

**Interfaces:**
- Consumes: everything from Tasks 1-11.
- Produces: nothing new — this is the final verification pass.

- [ ] **Step 1: Fix the misleading Swagger description**

In `backend/app.py`, the `Api(...)` constructor's `description` currently reads:

```python
        description=(
            "API para el sistema de tickets de soporte SYWork.\n\n"
            "**Nota de desarrollo**: autenticación desactivada (`DEV_SKIP_AUTH=true`). "
            "Todos los endpoints son accesibles sin token JWT durante el desarrollo de Fase 0."
        ),
```

Replace it with:

```python
        description=(
            "API para el sistema de tickets de soporte SYWork.\n\n"
            "**Nota de desarrollo**: las rutas de maestros (clients/projects/resources/skills/users/roles/permissions) "
            "no exigen JWT en esta fase. `/api/auth/login` (usuario/contraseña provisional) y `/api/auth/google` "
            "emiten un token real; `/api/auth/me` sí lo exige."
        ),
```

- [ ] **Step 2: Run the entire backend test suite**

Run: `docker exec sywork_backend python -m pytest tests/ -v`
Expected: every test passes, zero failures. If anything fails, do not move on — this plan touches nearly every backend file, and a failure here means an earlier task's step was skipped or mistyped.

- [ ] **Step 3: Manual smoke test against the real running server**

Run:
```bash
docker exec sywork_backend python -c "
from backend.app import create_app
app = create_app()
with app.test_client() as c:
    for email in ('admin@sywork.net', 'coordinador@sywork.net', 'qm@sywork.net', 'resolutor@sywork.net'):
        r = c.post('/api/auth/login', json={'username_or_email': email, 'password': 'definitely-wrong'})
        print(email, '->', r.status_code, r.get_json()['error'])

    r = c.get('/api/roles?page_size=100')
    print('roles:', [x['name'] for x in r.get_json()['items']])

    r = c.get('/api/permissions')
    print('permissions total:', r.get_json()['total'])

    r = c.get('/swagger.json')
    print('swagger.json:', r.status_code)
"
```
Expected: all 4 logins return `401 unauthorized` (wrong password, but proves the accounts exist and the endpoint works), `roles` lists `Admin, Coordinador, QM, Resolutor`, `permissions total: 24`, `swagger.json: 200`.

- [ ] **Step 4: Verify with the actual provisional password from Task 8**

If you still have the password printed during Task 8 Step 3, verify one real login end-to-end:
```bash
docker exec sywork_backend python -c "
from backend.app import create_app
app = create_app()
with app.test_client() as c:
    r = c.post('/api/auth/login', json={'username_or_email': 'admin@sywork.net', 'password': '<PASTE THE PASSWORD HERE>'})
    print(r.status_code, r.get_json())
"
```
Expected: `200`, with `role.name == "Admin"` and a `permissions` list containing all 24 entries.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py
git commit -m "docs(api): fix stale Swagger description referencing the old DEV_SKIP_AUTH bypass"
```

---

## Self-Review Notes

- **Spec coverage**: roles/permissions/role_permissions tables (Task 8) ✓; users.role_id/username/password_hash migration (Task 8) ✓; RoleRepository/PermissionRepository CRUD (Task 6, 9, 10) ✓; provisional login endpoint (Task 7, tested in Task 11) ✓; `/api/auth/me` enrichment (Task 7) ✓; 4 seed roles with the agreed permission matrix (Task 8) ✓; 4 seed users (Task 8) ✓; Admin-role deletion/deactivation protection (Task 3, 9) ✓; role/permission "in use" 409s (Task 3, 9, 10) ✓; DomainError status codes, not hardcoded 409s (all route tasks) ✓. **Not covered here, by design**: frontend (separate plan, see below), backend permission enforcement (explicitly out of scope per the approved spec).
- **Type consistency checked**: `RoleRepository.replace_permissions` takes `list[uuid.UUID]` and the route (Task 9) parses string IDs into UUIDs before calling it — consistent. `RoleService.validate_role_change`'s second parameter changed from a `Role` enum member to a plain `str` (Task 4) and its only call site (Task 7's `users.py`) passes `new_role.name`, a string — consistent. `UserRepository.update_role` changed from taking a `Role` object to a `role_id: uuid.UUID` (Task 6) and its only caller (Task 7's `users.py`) passes the parsed UUID — consistent.
- **Sequencing verified**: traced every top-level `from backend.domain.entities.user import ... Role` reference across the codebase (`conftest.py`, `user_repo.py`, `user_model.py`, `users.py`, `auth.py` route, `role_service.py`, `auth.py`/`rbac.py` middleware) and confirmed each is fixed no later than Task 7, before the first `pytest` run in Task 8. Arithmetic for the seeded `role_permissions` row count double-checked: Admin 24 + Coordinador 17 + QM 14 + Resolutor 5 = 60.
- **No placeholders**: every step has complete, runnable code.

## What's Next

This plan covers the backend only. Once it's implemented and the full test suite is green, a **second plan** covers the frontend (`LoginPage.tsx` rewrite, activating `ProtectedRoute`/`DashboardPage`, dynamic permission-driven menu in `config/navigation.tsx`, the new `RolesPermissionsPage.tsx` screen) — it depends on every endpoint built here existing first, which is why it's a separate plan rather than more tasks bolted onto this one.
