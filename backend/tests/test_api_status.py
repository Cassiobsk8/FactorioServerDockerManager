from backend.app import app
from backend.services.runtime_state_service import clear_pending


def test_api_status_returns_json_payload():
    client = app.test_client()
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert "status" in payload
    assert "runtime_state" in payload
    assert "server" in payload

    server = payload["server"]
    for field in ("ram_used_mb", "ram_total_mb", "disk_used_mb", "disk_total_mb"):
        assert field in server, f"missing metric field: {field}"

    assert isinstance(server["ram_used_mb"], (int, float))
    assert isinstance(server["ram_total_mb"], (int, float))
    assert isinstance(server["disk_used_mb"], (int, float))
    assert isinstance(server["disk_total_mb"], (int, float))

    # Old metric field names must no longer be present
    assert "ram_mb" not in server
    assert "disk_usage_mb" not in server


def test_api_status_active_save_is_object_or_none():
    client = app.test_client()
    response = client.get("/api/status")

    assert response.status_code == 200
    server = response.get_json()["server"]
    active_save = server.get("active_save")

    assert active_save is None or (
        isinstance(active_save, dict)
        and "name" in active_save
        and "size" in active_save
        and "modified" in active_save
    )


def test_api_status_includes_runtime_state_structure():
    client = app.test_client()
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.get_json()
    runtime = payload.get("runtime_state", {})
    assert "pending" in runtime
    assert "has_pending" in runtime
    assert "pending_keys" in runtime
