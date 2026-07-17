from __future__ import annotations

import socket
import struct
from typing import List
from unittest import mock

import pytest

from backend.services import rcon_service
from backend.services.rcon_service import (
    RCONService,
    RconAuthError,
    RconConnectionError,
    RconTimeoutError,
    _parse_players,
    apply_rcon_settings,
    get_rcon_service,
    get_rcon_status,
    reset_rcon_service,
)
from backend.services.settings_service import save_app_settings


@pytest.fixture(autouse=True)
def _reset_rcon_service():
    reset_rcon_service()
    yield
    reset_rcon_service()


def _pack(request_id: int, response_type: int, body: str) -> bytes:
    payload = struct.pack("<ii", request_id, response_type) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


class FakeSocket:
    """Minimal socket stub that replays a stream of scripted packets."""

    def __init__(self, packets: List[bytes], recv_side_effect=None):
        self._stream = b"".join(packets)
        self._pos = 0
        self.sent: List[bytes] = []
        self.timeout = 5
        self.closed = False
        self._recv_side_effect = recv_side_effect

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, n: int) -> bytes:
        if self._recv_side_effect is not None:
            effect = self._recv_side_effect
            self._recv_side_effect = None
            if isinstance(effect, Exception):
                raise effect
        if self._pos >= len(self._stream):
            return b""
        chunk = self._stream[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True

    def fileno(self) -> int:
        return 9999

    def gettimeout(self) -> Optional[float]:
        return self.timeout

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def setsockopt(self, level, optname, value):
        pass


def _auth_ok_socket() -> FakeSocket:
    # Auth request uses request id 1; server responds with id 1 on success.
    # A trailing empty SERVERDATA_RESPONSE_VALUE may follow and is drained
    # by _authenticate.
    return FakeSocket(
        packets=[
            _pack(1, 2, ""),
            _pack(1, 0, ""),
        ]
    )


def _cmd_response_socket(body: str, commands: int = 1) -> FakeSocket:
    # After auth (id 1), an empty trailing packet is drained by _authenticate.
    # Each exec command is sent with id 2, 3, ...
    packets = [_pack(1, 2, "")]
    packets.append(_pack(1, 0, ""))  # drained by _authenticate
    for cmd_id in range(2, 2 + commands):
        packets.append(_pack(cmd_id, 0, body))   # exec response
        packets.append(_pack(cmd_id, 0, ""))      # terminator
    return FakeSocket(packets=packets)



def test_connect_success_returns_true():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        assert service.connect() is True
        assert service.is_connected() is True
    fake.close()
    assert fake.closed is True


def test_connect_auth_failure_raises():
    fake = FakeSocket(packets=[_pack(-1, 2, ""), _pack(1, 0, "ignored")])
    service = RCONService(host="127.0.0.1", port=27015, password="wrong")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        with mock.patch.object(service, "_receive", return_value=(-1, "")):
            with pytest.raises(RconAuthError):
                service.connect()
    assert service.is_connected() is False


def test_connect_timeout_raises_rcon_timeout():
    service = RCONService(host="127.0.0.1", port=27015, password="secret", timeout=1)
    err = socket.timeout("timed out")
    with mock.patch.object(socket, "create_connection", side_effect=err):
        with pytest.raises(RconTimeoutError):
            service.connect()
    assert service.is_connected() is False


def test_connect_connection_refused_raises_rcon_connection_error():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    with mock.patch.object(socket, "create_connection", side_effect=ConnectionRefusedError("refused")):
        with pytest.raises(RconConnectionError):
            service.connect()


def test_execute_command_returns_response():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _cmd_response_socket("Player1, Player2")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        result = service.execute_command("/players")
    assert result == "Player1, Player2"


def test_execute_command_send_timeout_raises():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        with mock.patch.object(fake, "sendall", side_effect=socket.timeout("send timeout")):
            with pytest.raises(RconTimeoutError):
                service.execute_command("/players")


def test_get_players_parses_inline_list():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _cmd_response_socket("Players (2): Player1, Player2")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        players = service.get_players()
    assert players == ["Player1", "Player2"]


def test_get_players_parses_multiline_list():
    output = "Players (2):\n  Player1\n  Player2"
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _cmd_response_socket(output)
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        players = service.get_players()
    assert players == ["Player1", "Player2"]


def test_parse_players_handles_empty():
    assert _parse_players("") == []
    assert _parse_players("Players (0):") == []


def test_save_game_and_broadcast():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _cmd_response_socket("Saving game...", commands=2)
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        assert service.save_game() == "Saving game..."
        assert service.broadcast_message("hi") == "Saving game..."


def test_rcon_not_configured_error_when_no_password():
    save_app_settings({"rcon_password": ""})
    with pytest.raises(rcon_service.RconNotConfiguredError):
        rcon_service.build_rcon_service()


def test_get_rcon_status_reports_not_configured():
    save_app_settings({"rcon_password": ""})
    status = rcon_service.get_rcon_status()
    assert status["configured"] is False
    assert status["connected"] is False
    assert status["error"] is not None


def test_get_rcon_status_reports_connection_error(monkeypatch):
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "1", "rcon_password": "secret", "rcon_timeout": "1"})
    with mock.patch.object(socket, "create_connection", side_effect=ConnectionRefusedError("refused")):
        status = rcon_service.get_rcon_status()
    assert status["connected"] is False
    assert status["error"] is not None


def test_status_payload_has_no_password():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "1", "rcon_password": "supersecret", "rcon_timeout": "1"})
    status = rcon_service.get_rcon_status()
    assert "password" not in status
    assert "password" not in status.get("host", "")


def test_auth_success_with_original_request_id():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = FakeSocket(packets=[_pack(1, 2, "")])
    with mock.patch.object(socket, "create_connection", return_value=fake):
        assert service.connect() is True
    fake.close()


def test_auth_failure_returns_minus_one():
    service = RCONService(host="127.0.0.1", port=27015, password="wrong")
    fake = FakeSocket(packets=[_pack(-1, 2, "")])
    with mock.patch.object(socket, "create_connection", return_value=fake):
        with pytest.raises(RconAuthError):
            service.connect()
    assert service.is_connected() is False


def test_execute_command_returns_single_response():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    # Add a single response packet for request_id=2
    fake._stream += _pack(2, 0, "hello")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        result = service.execute_command("/say hello")
    assert result == "hello"


def test_execute_command_returns_multipacket_without_empty_terminator():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    # Multi-packet response without empty terminator
    fake._stream += _pack(2, 0, "part1") + _pack(2, 0, "part2")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        result = service.execute_command("/players")
    assert result == "part1part2"


def test_execute_command_ignores_different_request_id():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    # Different request_id arrives first and is buffered for the next read.
    # The current command returns empty because its response hasn't arrived yet.
    fake._stream += _pack(99, 0, "noise") + _pack(2, 0, "real")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        result = service.execute_command("/players")
    assert result == ""
    # The buffered packet (99, "noise") should be returned on the next read.
    resp_id, body = service._receive()
    assert resp_id == 99
    assert body == "noise"


def test_execute_command_receive_timeout_raises():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        with mock.patch.object(fake, "recv", side_effect=socket.timeout("recv timeout")):
            with pytest.raises(RconTimeoutError):
                service.execute_command("/players")


def test_receive_invalid_packet_size_raises():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = FakeSocket(packets=[struct.pack("<i", 0)])
    with mock.patch.object(socket, "create_connection", return_value=fake):
        with pytest.raises(RconConnectionError):
            service.connect()


def test_send_packet_uses_two_null_terminators():
    service = RCONService(host="127.0.0.1", port=27015, password="secret")
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "response")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service.connect()
        service.execute_command("/players")
    sent = fake.sent[-1]
    assert sent.endswith(b"\x00\x00")
    size = struct.unpack("<i", sent[:4])[0]
    assert size == len(sent) - 4


def test_persistent_service_reuses_connection():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "ok")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        first = service.execute_command("/players")
        assert first == "ok"
        assert service.is_connected() is True
        fake._stream += _pack(3, 0, "ok2")
        second = service.execute_command("/players")
        assert second == "ok2"
        assert service.is_connected() is True
        assert len(fake.sent) > 0


def test_persistent_service_reconnects_after_socket_error():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "first")
    # After first connection: _request_id=2 (1 auth + 1 cmd)
    # Failed second command uses _next_id()=3, then reconnect uses auth request_id=4
    # and command request_id=5.
    fake2 = FakeSocket(packets=[_pack(4, 2, ""), _pack(4, 0, ""), _pack(5, 0, "retry")])
    with mock.patch.object(socket, "create_connection", side_effect=[fake, fake2]):
        service = get_rcon_service()
        service.connect()
        assert service.execute_command("/players") == "first"
        result = service.execute_command("/players")
        assert result == "retry"
        assert service.reconnect_count >= 2


def test_persistent_service_metrics():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "metric")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.connected_since is not None
        assert service.reconnect_count == 1
        service.execute_command("/players")
        assert service.last_command == "/players"
        assert service.last_response_time is not None
        assert service.last_response_time > 0


def test_reset_rcon_service_disconnects():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.is_connected() is True
        reset_rcon_service()
        assert service.is_connected() is False


def test_apply_rcon_settings_resets_singleton():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.is_connected() is True
    apply_rcon_settings(host="127.0.0.1", port=27015, password="newpass", timeout=5)
    assert rcon_service._rcon_service is None


def test_get_rcon_status_includes_metrics():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "ok")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        status = get_rcon_status()
    assert status["connected"] is True
    assert status["connected_since"] is not None
    assert status["reconnect_count"] == 1
    assert status["last_command"] is None
    assert status["last_response_time"] is None


def test_get_rcon_players_executes_players_command():
    save_app_settings({"rcon_host": "127.0.0.1", "rcon_port": "27015", "rcon_password": "secret", "rcon_timeout": "5"})
    fake = _cmd_response_socket("Players (2): Player1, Player2")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        result = rcon_service.get_rcon_players()
    assert result["connected"] is True
    assert result["players"] == ["Player1", "Player2"]
    assert result["player_count"] == 2
    assert result["error"] is None
