import uuid

import pytest

from backend.domain.services.skill_service import SkillService, SkillBusinessError


class FakeResourcesRepo:
    def __init__(self, active_count=0):
        self._active_count = active_count

    def count_active_resources_with_skill(self, skill_id):
        return self._active_count


def test_validate_delete_passes_when_unused():
    svc = SkillService()
    svc.validate_delete(uuid.uuid4(), resources_repo=FakeResourcesRepo(active_count=0))


def test_validate_delete_raises_409_with_resource_count_when_in_use():
    svc = SkillService()
    with pytest.raises(SkillBusinessError) as exc_info:
        svc.validate_delete(uuid.uuid4(), resources_repo=FakeResourcesRepo(active_count=2))
    err = exc_info.value
    assert err.code == "skill_in_use"
    assert err.status_code == 409
    assert err.extra == {"resource_count": 2}


def test_validate_delete_passes_when_no_repo_given():
    svc = SkillService()
    svc.validate_delete(uuid.uuid4(), resources_repo=None)
