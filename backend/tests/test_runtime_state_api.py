from unittest.mock import patch

from backend.app import app
from backend.services.runtime_state_service import clear_pending, mark_pending


def test_api_runtime_state_returns_empty_by_default():
    clear_pending()
    client = app.test_client()
    response = client.get("/api/runtime-state")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["has_pending"] is False
    assert payload["pending_keys"] == []


def test_api_runtime_state_clear_removes_pending():
    mark_pending("whitelist")
    client = app.test_client()
    response = client.post("/api/runtime-state/clear")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["has_pending"] is False
    assert payload["pending_keys"] == []


def test_api_restart_clears_pending():
    mark_pending("whitelist")
    client = app.test_client()
    with patch("backend.routes.api_routes.factorio_service.restart_server"):
        response = client.post("/api/restart")
    assert response.status_code == 200
    assert response.get_json()["status"] == "restarted"
