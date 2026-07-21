from __future__ import annotations

import json
import socket
import struct
from pathlib import Path
from unittest import mock

import pytest

from backend.app import app
from backend.services.rcon_service import RconConnectionError, RconTimeoutError, reset_rcon_service
from backend.services.runtime_session import get_runtime_session, reset_runtime_session
from backend.services.settings_service import save_app_settings

BASE = Path(__file__).resolve().parent.parent.parent
SETTINGS_PATH = BASE / "data" / "settings.json"


@pytest.fixture(autouse=True)
def _reset_rcon_service():
    reset_rcon_service()
    yield
    reset_rcon_service()


def _reset_settings():
    if SETTINGS_PATH.exists():
        try:
            SETTINGS_PATH.unlink()
        except OSError:
            pass


@pytest.fixture(autouse=True)
def _clean_settings():
    _reset_settings()
    yield
    _reset_settings()


def test_translations_include_rcon_keys():
    client = app.test_client()
    for lang in ("en", "pt_BR", "es", "zh_CN"):
        res = client.get(f"/api/translations/{lang}")
        assert res.status_code == 200, lang
        data = res.get_json()
        for key in (
            "menu.console",
            "rcon.console_title",
            "rcon.quick_actions",
            "rcon.save_world",
            "rcon.players_online",
            "rcon.server_status",
            "rcon.broadcast",
            "rcon.send",
            "rcon.no_players",
            "rcon.execute",
            "rcon.command_placeholder",
            "rcon.history_hint",
            "rcon.settings_title",
            "rcon.test_connection",
            "rcon.save_settings",
        ):
            assert key in data, f"{lang} missing key {key}"


def test_rcon_test_button_connection_refused_returns_connected_false():
    client = app.test_client()
    res = client.post(
        "/api/rcon/test",
        json={"host": "127.0.0.1", "port": 1, "password": "secret", "timeout": 1},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["connected"] is False
    assert "error" in payload and payload["error"]


def test_rcon_test_button_timeout_returns_connected_false():
    client = app.test_client()
    res = client.post(
        "/api/rcon/test",
        json={"host": "10.255.255.1", "port": 27015, "password": "secret", "timeout": 1},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["connected"] is False


def test_rcon_settings_persistence_roundtrip():
    client = app.test_client()
    res = client.post(
        "/api/rcon/settings",
        json={"host": "192.168.1.50", "port": 27015, "password": "topsecret", "timeout": 7},
    )
    assert res.status_code == 200
    saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["rcon_host"] == "192.168.1.50"
    assert int(saved["rcon_port"]) == 27015
    assert saved["rcon_password"] == "topsecret"
    assert int(saved["rcon_timeout"]) == 7

    # Settings are reflected back via GET and the password is returned.
    res = client.get("/api/rcon/settings")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["host"] == "192.168.1.50"
    assert payload["port"] == 27015
    assert payload["password"] == "topsecret"
    assert payload["configured"] is True


def test_rcon_status_not_configured():
    save_app_settings({"rcon_password": ""})
    client = app.test_client()
    res = client.get("/api/rcon/status")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["configured"] is False
    assert payload["connected"] is False
    assert payload["error"] is not None
    assert "password" not in payload


def test_rcon_status_disconnected_when_offline():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "1", "rcon_password": "secret", "rcon_timeout": "1"})
    client = app.test_client()
    res = client.get("/api/rcon/status")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["configured"] is True
    assert payload["connected"] is False
    assert payload["error"] is None
    assert "password" not in payload


def test_rcon_status_connected_with_mock_server():
    import socket

    from backend.services import rcon_service

    def _pack(request_id, response_type, body):
        payload = struct.pack("<ii", request_id, response_type) + body.encode("utf-8") + b"\x00\x00"
        return struct.pack("<i", len(payload)) + payload

    class FakeSocket:
        def __init__(self):
            self._stream = _pack(1, 2, "") + _pack(1, 0, "")
            self._pos = 0
            self.sent = []
            self.closed = False
            self.timeout = 5

        def sendall(self, data):
            self.sent.append(data)

        def recv(self, n):
            chunk = self._stream[self._pos:self._pos + n]
            self._pos += len(chunk)
            return chunk

        def close(self):
            self.closed = True

        def fileno(self):
            return 9999

        def gettimeout(self):
            return self.timeout

        def settimeout(self, value):
            self.timeout = value

        def setsockopt(self, level, optname, value):
            pass

    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})

    def _fake_create_connection(addr, timeout=None):
        return FakeSocket()

    with mock.patch.object(socket, "create_connection", side_effect=_fake_create_connection):
        service = rcon_service.get_rcon_service()
        service.connect()
        status = rcon_service.get_rcon_status()

    assert status["connected"] is True
    assert status["configured"] is True
    assert "password" not in status


def test_rcon_command_requires_configuration():
    save_app_settings({"rcon_password": ""})
    client = app.test_client()
    res = client.post("/api/rcon/command", json={"command": "/players"})
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["connected"] is False
    assert "error" in payload


def test_rcon_players_does_not_connect_when_server_stopped():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "1", "rcon_password": "secret", "rcon_timeout": "1"})
    client = app.test_client()
    res = client.get("/api/rcon/players")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["connected"] is False
    assert payload["players"] == []
    assert payload["player_count"] == 0
    assert payload["error"] == "Server not running"


def test_rcon_players_does_not_connect_when_rcon_disabled():
    save_app_settings({"rcon_password": ""})
    client = app.test_client()
    res = client.get("/api/rcon/players")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["connected"] is False
    assert payload["players"] == []
    assert payload["player_count"] == 0
    assert "not configured" in payload["error"]


def test_rcon_players_does_not_connect_when_not_connected():
    from backend.services import runtime_session

    runtime_session.reset_runtime_session()
    runtime_session.get_runtime_session().start(pid=12345)

    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    client = app.test_client()
    res = client.get("/api/rcon/players")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["connected"] is False
    assert payload["players"] == []
    assert payload["player_count"] == 0
    assert payload["error"] == "RCON not connected"
