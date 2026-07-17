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
    apply_rcon_settings,
    get_rcon_service,
    get_rcon_status,
    reset_rcon_service,
    attempt_rcon_connection,
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
    """Replays a fixed stream of scripted packets, then EOF."""

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

    def gettimeout(self) -> float:
        return self.timeout

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def setsockopt(self, level, optname, value):
        pass


def _auth_ok_socket() -> FakeSocket:
    return FakeSocket(packets=[_pack(1, 2, ""), _pack(1, 0, "")])


def _cmd_response_socket(body: str, commands: int = 1) -> FakeSocket:
    packets = [_pack(1, 2, ""), _pack(1, 0, "")]
    for cmd_id in range(2, 2 + commands):
        packets.append(_pack(cmd_id, 0, body))
        packets.append(_pack(cmd_id, 0, ""))
    return FakeSocket(packets=packets)


def _configured():
    save_app_settings({
        "rcon_host": "127.0.0.1",
        "rcon_port": "27015",
        "rcon_password": "secret",
        "rcon_timeout": "5",
    })


# 1. Conexao persistente: apenas UMA instancia/socket por singleton
def test_persistent_connection_uses_single_socket():
    _configured()
    # auth(id=1), depois comandos id=2,3,4,5
    fake = _auth_ok_socket()
    for cmd_id in range(2, 6):
        fake._stream += _pack(cmd_id, 0, f"r{cmd_id}")
        fake._stream += _pack(cmd_id, 0, "")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.is_connected()
        # executa varios comandos; o socket nunca e recriado
        for i in range(1, 4):
            assert service.execute_command("/players") == f"r{1 + i}"
        assert service.reconnect_count == 1
        assert fake.closed is False


# 2. Test Connection usa SEGUNDA instancia efemera e a encerra
def test_test_connection_creates_disconnected_secondary_instance():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        result = attempt_rcon_connection(host="127.0.0.1", port=27015, password="secret")
    # a conexao de teste foi fechada no finally
    assert result["connected"] is True
    assert fake.closed is True
    # o singleton persistente continua intocado
    assert rcon_service._rcon_service is None


def test_test_connection_with_temporary_credentials_does_not_change_singleton():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        # configuracao temporaria diferente da persistida
        result = attempt_rcon_connection(host="10.0.0.5", port=27016, password="temp")
    assert result["connected"] is True
    assert rcon_service._rcon_service is None


def test_test_connection_failure_reports_error():
    with mock.patch.object(socket, "create_connection", side_effect=ConnectionRefusedError("refused")):
        result = attempt_rcon_connection(host="127.0.0.1", port=1, password="secret")
    assert result["connected"] is False
    assert result["error"]


# 3. Status: unica fonte de verdade
def test_status_uses_persistent_connection_state():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        status = get_rcon_status()
    assert status["connected"] is True
    assert status["configured"] is True
    assert "password" not in status


def test_status_reports_disconnected_when_socket_drops():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.is_connected()
        # simula perda da conexao real
        service._close_socket()
        status = get_rcon_status()
    # tenta reconectar e, como o fake ja foi consumido, deve falhar de forma real
    assert status["connected"] is False
    assert status["error"]


# 4. Polling: get_rcon_status e redirecionamento de estado
def test_status_endpoint_reflects_real_state_across_calls():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        first = get_rcon_status()
        second = get_rcon_status()
    # segunda chamada reaproveita o socket (ja conectado)
    assert first["connected"] is True
    assert second["connected"] is True
    assert second["reconnect_count"] == first["reconnect_count"]


# 5. Players
def test_players_end_to_end():
    _configured()
    fake = _cmd_response_socket("Players (3): A, B, C")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        from backend.services.rcon_service import get_rcon_players
        result = get_rcon_players()
    assert result["connected"] is True
    assert result["players"] == ["A", "B", "C"]
    assert result["player_count"] == 3


def test_players_handles_connection_error():
    save_app_settings({
        "rcon_host": "127.0.0.1",
        "rcon_port": "1",
        "rcon_password": "secret",
        "rcon_timeout": "1",
    })
    with mock.patch.object(socket, "create_connection", side_effect=ConnectionRefusedError("refused")):
        from backend.services.rcon_service import get_rcon_players
        result = get_rcon_players()
    assert result["connected"] is False
    assert result["player_count"] == 0


# 6. Save
def test_save_game_end_to_end():
    _configured()
    fake = _cmd_response_socket("Saving game...", commands=1)
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.save_game() == "Saving game..."


# 7. Broadcast
def test_broadcast_end_to_end():
    _configured()
    fake = _cmd_response_socket("Broadcasting...", commands=1)
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.broadcast_message("hello") == "Broadcasting..."


# 8. Reconnect automatico apos perda da conexao
def test_execute_reconnects_after_socket_loss():
    _configured()
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "first")
    fake2 = FakeSocket(packets=[_pack(3, 2, ""), _pack(3, 0, ""), _pack(4, 0, "retry")])
    with mock.patch.object(socket, "create_connection", side_effect=[fake, fake2]):
        service = get_rcon_service()
        service.connect()
        assert service.execute_command("/players") == "first"
        # forca perda da conexao antes do segundo comando
        service._close_socket()
        assert service.execute_command("/players") == "retry"
        assert service.reconnect_count >= 2


# 9. Perda de conexao durante receive levanta erro real
def test_connection_loss_during_receive_raises():
    _configured()
    fake = _auth_ok_socket()
    fake._stream += _pack(2, 0, "partial")
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        service.execute_command("/players")  # consome resposta
        # proxima leitura encontra EOF -> RconConnectionError real
        with pytest.raises(RconConnectionError):
            service._receive()


# 10. Timeout
def test_execute_command_timeout_raises():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        with mock.patch.object(fake, "recv", side_effect=socket.timeout("recv timeout")):
            with pytest.raises(RconTimeoutError):
                service.execute_command("/players")


# 11. Alteracao de configuracao invalida a instancia antiga
def test_apply_settings_resets_persistent_instance():
    _configured()
    fake = _auth_ok_socket()
    with mock.patch.object(socket, "create_connection", return_value=fake):
        service = get_rcon_service()
        service.connect()
        assert service.is_connected()
    apply_rcon_settings(host="127.0.0.1", port=27015, password="newpass", timeout=5)
    # o singleton foi resetado; nova instancia carrega a nova senha
    assert rcon_service._rcon_service is None
    saved = rcon_service._load_rcon_settings()
    assert saved["password"] == "newpass"


def test_status_unconfigured_does_not_create_instance():
    save_app_settings({"rcon_password": ""})
    status = get_rcon_status()
    assert status["configured"] is False
    assert status["connected"] is False
    assert status["error"]
    assert rcon_service._rcon_service is None


# 12. send_rcon_command / build_rcon_service removidos (codigo morto) - verificacao
def test_legacy_helpers_removed():
    assert not hasattr(rcon_service, "send_rcon_command")
    assert not hasattr(rcon_service, "build_rcon_service")
    assert not hasattr(rcon_service, "get_server_status")
