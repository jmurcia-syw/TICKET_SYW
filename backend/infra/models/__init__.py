from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from backend.infra.models.role_model import RoleModel, PermissionModel  # noqa: E402, F401
from backend.infra.models.user_model import UserModel  # noqa: E402, F401
from backend.infra.models.client_model import ClientModel  # noqa: E402, F401
from backend.infra.models.project_model import ProjectModel  # noqa: E402, F401
from backend.infra.models.resource_model import SkillModel, ResourceModel  # noqa: E402, F401
