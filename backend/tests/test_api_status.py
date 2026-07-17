from backend.app import app


def test_api_status_returns_json_payload():
    client = app.test_client()
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert "status" in payload
    assert "server" in payload
