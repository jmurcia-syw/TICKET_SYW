import uuid

import pytest

from backend.domain.services.compensation_service import (
    CompensationService, CompensationBusinessError, MONTHLY_WORK_HOURS,
)

svc = CompensationService()
RESOURCE_ID = uuid.uuid4()


def test_hourly_cost_from_total_salary_and_overhead():
    comp = svc.build(RESOURCE_ID, base_salary=4000, total_salary=6000, overhead=1200)
    assert comp.hourly_cost == round(7200 / MONTHLY_WORK_HOURS, 2)


def test_hourly_cost_without_overhead():
    comp = svc.build(RESOURCE_ID, base_salary=None, total_salary=4800, overhead=None)
    assert comp.hourly_cost == round(4800 / MONTHLY_WORK_HOURS, 2)


def test_hourly_cost_none_without_total_salary():
    comp = svc.build(RESOURCE_ID, base_salary=4000, total_salary=None, overhead=500)
    assert comp.hourly_cost is None


def test_negative_amount_rejected():
    with pytest.raises(CompensationBusinessError) as exc:
        svc.build(RESOURCE_ID, base_salary=-1, total_salary=None, overhead=None)
    assert exc.value.code == "invalid_amount"
    assert exc.value.status_code == 400


def test_total_salary_lower_than_base_rejected():
    with pytest.raises(CompensationBusinessError) as exc:
        svc.build(RESOURCE_ID, base_salary=5000, total_salary=4000, overhead=None)
    assert exc.value.code == "invalid_amount"


def test_currency_defaults_to_usd():
    comp = svc.build(RESOURCE_ID, base_salary=None, total_salary=None, overhead=None, currency="")
    assert comp.currency == "USD"


def test_currency_preserved():
    comp = svc.build(RESOURCE_ID, base_salary=None, total_salary=1000, overhead=None, currency="COP")
    assert comp.currency == "COP"
