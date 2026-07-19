from unittest.mock import patch

from backend.app import app
from backend.services.runtime_state_service import clear_pending, mark_pending
from backend.services.startup_validation_service import validate_startup


def test_api_validate_startup_returns_valid_when_all_ok():
    with patch("backend.routes.api_routes.validate_startup", return_value={"valid": True, "errors": []}):
        client = app.test_client()
        response = client.post("/api/validate-startup")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["valid"] is True
        assert payload["errors"] == []


def test_api_validate_startup_returns_errors():
    errors = [{"code": "no_active_save", "message": "No active save configured"}]
    with patch("backend.routes.api_routes.validate_startup", return_value={"valid": False, "errors": errors}):
        client = app.test_client()
        response = client.post("/api/validate-startup")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["valid"] is False
        assert payload["errors"] == errors


def test_api_validate_startup_handles_exception():
    with patch("backend.routes.api_routes.validate_startup", side_effect=RuntimeError("boom")):
        client = app.test_client()
        response = client.post("/api/validate-startup")
        assert response.status_code == 500
