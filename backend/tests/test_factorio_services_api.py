from unittest.mock import patch

from backend.app import app
from backend.services.factorio_services_service import save_factorio_services


def test_api_factorio_services_get_not_configured():
    with patch("backend.routes.api_routes.get_factorio_services_status", return_value={"status": "not_configured", "username": "", "token_masked": ""}):
        client = app.test_client()
        response = client.get("/api/factorio-services")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "not_configured"


def test_api_factorio_services_get_authenticated():
    with patch("backend.routes.api_routes.get_factorio_services_status", return_value={"status": "authenticated", "username": "user", "token_masked": "user****oken"}):
        client = app.test_client()
        response = client.get("/api/factorio-services")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "authenticated"
    assert payload["username"] == "user"
    assert "token_masked" in payload


def test_api_factorio_services_save_success():
    with patch("backend.routes.api_routes.save_factorio_services", return_value={"factorio_username": "user", "factorio_service_token": "toke****"}):
        client = app.test_client()
        response = client.post("/api/factorio-services", json={"username": "user", "token": "token123"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["factorio_username"] == "user"


def test_api_factorio_services_save_missing_fields():
    client = app.test_client()
    response = client.post("/api/factorio-services", json={"username": "", "token": ""})
    assert response.status_code == 400


def test_api_status_includes_factorio_account():
    with patch("backend.routes.api_routes.get_factorio_services_status", return_value={"status": "not_configured", "username": "", "token_masked": ""}):
        client = app.test_client()
        response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert "factorio_account" in payload
    assert payload["factorio_account"]["status"] == "not_configured"
