"""absence_service — dominio puro, sin DB (spec 020, Fase 5, Historia 2).

Ultra-limitado (Principio VII): fixtures en memoria, sin inserts a base de datos.
"""
from datetime import date
import uuid

import pytest

from backend.domain.entities.calendar import AbsenceRequest
from backend.domain.services import absence_service as svc

RESOURCE_ID = uuid.uuid4()
OTHER_RESOURCE_ID = uuid.uuid4()


def _request(**overrides) -> AbsenceRequest:
    defaults = dict(
        id=uuid.uuid4(), resource_id=RESOURCE_ID, absence_type_id=uuid.uuid4(),
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
    )
    defaults.update(overrides)
    return AbsenceRequest(**defaults)


def test_overall_status_pending_por_defecto():
    assert svc.overall_status("pending", "pending") == "pending"


def test_overall_status_approved_solo_si_ambos_aprueban():
    assert svc.overall_status("approved", "pending") == "pending"
    assert svc.overall_status("approved", "approved") == "approved"


def test_overall_status_rejected_si_cualquiera_rechaza():
    assert svc.overall_status("rejected", "approved") == "rejected"
    assert svc.overall_status("approved", "rejected") == "rejected"


def test_manager_status_inicial_auto_aprobado_sin_jefe():
    """FR-011b: sin manager_id en el recurso, esa mitad nace ya resuelta."""
    assert svc.initial_manager_status(has_manager=False) == "approved"
    assert svc.initial_manager_status(has_manager=True) == "pending"


def test_bloquea_decision_sobre_la_propia_solicitud():
    """FR-012: ni el Jefe ni RRHH deciden sobre su propia solicitud."""
    request = _request()
    with pytest.raises(svc.AbsenceServiceError) as exc:
        svc.assert_not_own_request(RESOURCE_ID, request)
    assert exc.value.code == "own_request"
    svc.assert_not_own_request(OTHER_RESOURCE_ID, request)  # no lanza


def test_bloquea_segunda_decision_del_mismo_lado():
    request = _request(manager_status="approved")
    with pytest.raises(svc.AbsenceServiceError) as exc:
        svc.assert_can_decide("manager", request)
    assert exc.value.code == "already_decided"
    svc.assert_can_decide("hr", request)  # hr sigue pending, no lanza


def test_rango_de_fechas_invalido():
    with pytest.raises(svc.AbsenceServiceError):
        svc.validate_date_range(date(2026, 8, 5), date(2026, 8, 1))
    svc.validate_date_range(date(2026, 8, 1), date(2026, 8, 1))  # no lanza


def test_bloquea_solapamiento_de_fechas():
    with pytest.raises(svc.AbsenceServiceError) as exc:
        svc.assert_no_overlap([_request()])
    assert exc.value.code == "overlap"
    svc.assert_no_overlap([])  # no lanza
