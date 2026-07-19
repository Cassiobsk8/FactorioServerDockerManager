from unittest.mock import patch

from backend.app import app


def test_api_startup_preview_returns_command():
    client = app.test_client()
    with patch("backend.routes.api_routes._factorio_command_impl") as mock_cmd:
        mock_cmd.return_value = [
            "/factorio/bin/x64/factorio",
            "--start-server=save.zip",
            "--server-settings=/factorio/config/server-settings.json",
            "--rcon-port=27015",
            "--rcon-password=secret",
        ]
        response = client.get("/api/startup-preview")
    assert response.status_code == 200
    payload = response.get_json()
    assert "command" in payload
    assert payload["command"][0] == "/factorio/bin/x64/factorio"
    assert payload["command"][1] == "--start-server=save.zip"
    assert not any(part.startswith("--rcon-password=secret") for part in payload["command"])
    assert any(part == "--rcon-password=******" for part in payload["command"])


def test_api_startup_preview_handles_error():
    client = app.test_client()
    with patch("backend.routes.api_routes._factorio_command_impl", side_effect=RuntimeError("boom")):
        response = client.get("/api/startup-preview")
    assert response.status_code == 500
    assert response.get_json()["error"] == "boom"
