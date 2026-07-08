import uuid
from datetime import date, timedelta

import pytest

from backend.domain.services.work_session_service import WorkSessionService


class FakeWorkSessionsRepo:
    def __init__(self, rows):
        self._rows = rows

    def aggregate_by_resource_and_day(self, resource_id, date_from, date_to):
        if resource_id is None:
            return self._rows
        return [r for r in self._rows if r["resource_id"] == resource_id]


@pytest.fixture()
def svc():
    return WorkSessionService()


def test_get_daily_summary_fills_missing_days_as_sin_registro(svc):
    resource_id = uuid.uuid4()
    today = date.today()
    yesterday = today - timedelta(days=1)
    repo = FakeWorkSessionsRepo(rows=[
        {"resource_id": resource_id, "work_date": yesterday, "total_minutes": 90},
    ])
    summary = svc.get_daily_summary(resource_id=resource_id, date_from=yesterday, date_to=today,
                                    work_sessions_repo=repo)
    days_by_date = {d["work_date"]: d for d in summary["days"]}
    assert days_by_date[yesterday]["total_minutes"] == 90
    assert days_by_date[yesterday]["sin_registro"] is False
    assert days_by_date[today]["total_minutes"] == 0
    assert days_by_date[today]["sin_registro"] is True
    assert summary["total_minutes"] == 90


def test_get_all_resources_summary_aggregates_across_days(svc):
    r1, r2 = uuid.uuid4(), uuid.uuid4()
    today = date.today()
    repo = FakeWorkSessionsRepo(rows=[
        {"resource_id": r1, "work_date": today, "total_minutes": 60},
        {"resource_id": r1, "work_date": today - timedelta(days=1), "total_minutes": 30},
        {"resource_id": r2, "work_date": today, "total_minutes": 120},
    ])
    overview = svc.get_all_resources_summary(date_from=today - timedelta(days=1), date_to=today,
                                             work_sessions_repo=repo)
    totals = {row["resource_id"]: row["total_minutes"] for row in overview}
    assert totals[r1] == 90
    assert totals[r2] == 120
