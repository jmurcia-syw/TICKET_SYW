from backend.domain.errors import DomainError
from backend.domain.services.client_service import ClientBusinessError
from backend.domain.services.project_service import ProjectBusinessError
from backend.domain.services.role_service import RoleBusinessError
from backend.domain.services.skill_service import SkillBusinessError


def test_domain_error_defaults_to_409():
    err = DomainError("some_code", "some message")
    assert err.code == "some_code"
    assert err.message == "some message"
    assert err.status_code == 409
    assert err.extra == {}


def test_domain_error_accepts_explicit_status_code():
    err = DomainError("not_found_code", "missing", status_code=404)
    assert err.status_code == 404


def test_domain_error_carries_extra_context():
    err = DomainError("in_use", "still referenced", resource_count=3)
    assert err.extra == {"resource_count": 3}


def test_business_error_subclasses_share_domain_error_behavior():
    for cls in (ClientBusinessError, ProjectBusinessError, RoleBusinessError, SkillBusinessError):
        err = cls("code", "message")
        assert isinstance(err, DomainError)
        assert err.status_code == 409  # default unless overridden at raise site
