"""Test unitario ultra-limitado (Principio VII) del cliente HTTP de festivos (spec 021).

Mockea `requests.get` — sin llamadas de red reales en tests.
"""
from unittest.mock import Mock, patch

import pytest
import requests

from backend.infra.external.holiday_api_client import HolidayApiError, fetch_public_holidays


def test_fetch_public_holidays_parses_response() -> None:
    payload = [
        {"date": "2026-07-20", "localName": "Declaracion de la Independencia de Colombia",
         "name": "Declaration of Independence"},
        {"date": "2026-01-01", "localName": "Año Nuevo", "name": "New Year's Day"},
    ]
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = payload

    with patch("backend.infra.external.holiday_api_client.requests.get", return_value=mock_response) as mock_get:
        result = fetch_public_holidays("CO", 2026)

    mock_get.assert_called_once()
    assert len(result) == 2
    assert result[0]["name"] == "Declaracion de la Independencia de Colombia"
    assert result[0]["holiday_date"].isoformat() == "2026-07-20"


def test_fetch_public_holidays_raises_on_timeout() -> None:
    with patch("backend.infra.external.holiday_api_client.requests.get",
              side_effect=requests.Timeout("timed out")):
        with pytest.raises(HolidayApiError):
            fetch_public_holidays("CO", 2026)


def test_fetch_public_holidays_raises_on_unknown_country() -> None:
    mock_response = Mock(status_code=404)

    with patch("backend.infra.external.holiday_api_client.requests.get", return_value=mock_response):
        with pytest.raises(HolidayApiError):
            fetch_public_holidays("ZZ", 2026)
