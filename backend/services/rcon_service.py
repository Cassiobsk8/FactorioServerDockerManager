from __future__ import annotations

import logging
import socket
import struct
import time
from typing import Optional

from backend.services.settings_service import load_app_settings, save_app_settings

logger = logging.getLogger("fsm.rcon")

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

DEFAULT_RCON_HOST = "127.0.0.1"
DEFAULT_RCON_PORT = 27015
DEFAULT_RCON_TIMEOUT = 5


class RconConnectionError(Exception):
    """Raised when the RCON server cannot be reached."""


class RconAuthError(Exception):
    """Raised when authentication with the RCON server fails."""


class RconTimeoutError(Exception):
    """Raised when an RCON operation times out."""


class RconNotConfiguredError(Exception):
    """Raised when RCON settings are not configured."""


def _load_rcon_settings() -> dict[str, str]:
    settings = load_app_settings()
    return {
        "host": settings.get("rcon_host", DEFAULT_RCON_HOST),
        "port": int(settings.get("rcon_port", DEFAULT_RCON_PORT)),
        "password": settings.get("rcon_password", ""),
        "timeout": int(settings.get("rcon_timeout", DEFAULT_RCON_TIMEOUT)),
    }


class RCONService:
    """Thin client for the Factorio RCON protocol (Source RCON).

    Responsibilities:
        - connect / disconnect to the RCON server
        - execute arbitrary admin commands
        - fetch the online player list
        - save the world
        - broadcast a message to all players
        - report server connection status
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, password: str = "", timeout: int = DEFAULT_RCON_TIMEOUT):
        self.host = host or DEFAULT_RCON_HOST
        self.port = port or DEFAULT_RCON_PORT
        self.password = password
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._request_id = 0
        self._pending_packet: Optional[tuple[int, str]] = None
        self._connected_since: Optional[float] = None
        self._reconnect_count: int = 0
        self._last_command: Optional[str] = None
        self._last_response_time: Optional[float] = None
        logger.info("[RCON INSTANCE CREATED] id=%s host=%s port=%s", id(self), self.host, self.port)

    @property
    def connected_since(self) -> Optional[float]:
        return self._connected_since

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    @property
    def last_command(self) -> Optional[str]:
        return self._last_command

    @property
    def last_response_time(self) -> Optional[float]:
        return self._last_response_time

    def is_connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> bool:
        """Open the socket and authenticate.

        Returns True when authentication succeeds, raises otherwise.
        """
        if self._socket is not None:
            logger.info("[RCON CONNECT] id=%s socket_fileno=%s already_connected=True", id(self), self._socket.fileno())
            return True

        try:
            logger.info("[RCON CONNECT] id=%s socket_fileno=None -> connecting to %s:%s (timeout=%ss)", id(self), self.host, self.port, self.timeout)
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except socket.timeout as exc:
            logger.warning("[RCON TIMEOUT] id=%s socket_fileno=None host=%s port=%s detail=connection_timeout", id(self), self.host, self.port)
            raise RconTimeoutError("RCON connection timed out") from exc
        except ConnectionRefusedError as exc:
            logger.warning("[RCON CONNECT] id=%s socket_fileno=None host=%s port=%s refused=True detail=%s", id(self), self.host, self.port, exc)
            raise RconConnectionError("Could not connect to RCON server: connection refused") from exc
        except OSError as exc:
            logger.warning("[RCON CONNECT] id=%s socket_fileno=None host=%s port=%s detail=%s", id(self), self.host, self.port, exc)
            raise RconConnectionError(f"Could not connect to RCON server: {exc}") from exc

        self._socket = sock
        self._connected_since = time.time()
        self._reconnect_count += 1
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        try:
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
            self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2)
        except (AttributeError, OSError):
            pass
        logger.info("[RCON CONNECT] id=%s socket_fileno=%s connected_since=%s reconnect_count=%s", id(self), self._socket.fileno(), self._connected_since, self._reconnect_count)
        try:
            self._authenticate()
        except RconAuthError:
            logger.error("[RCON AUTH] id=%s socket_fileno=%s host=%s port=%s result=failed", id(self), self._socket.fileno(), self.host, self.port)
            self._close_socket()
            raise
        except Exception:
            logger.error("[RCON ERROR] id=%s socket_fileno=%s host=%s port=%s detail=auth_handshake_exception", id(self), self._socket.fileno() if self._socket else None, self.host, self.port)
            self._close_socket()
            raise
        logger.info("[RCON CONNECT] id=%s socket_fileno=%s host=%s port=%s authenticated=True", id(self), self._socket.fileno(), self.host, self.port)
        return True

    def disconnect(self) -> None:
        logger.info("[RCON DISCONNECT] id=%s socket_fileno=%s", id(self), self._socket.fileno() if self._socket else None)
        self._close_socket()

    def _close_socket(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
            self._connected_since = None

    def _authenticate(self) -> None:
        if not self.password:
            logger.warning("[RCON AUTH] id=%s socket_fileno=%s host=%s port=%s result=skipped detail=empty_password", id(self), self._socket.fileno() if self._socket else None, self.host, self.port)
            raise RconAuthError("RCON password is empty")
        request_id = self._send(SERVERDATA_AUTH, self.password)
        logger.info("[RCON AUTH] id=%s socket_fileno=%s request_id=%s", id(self), self._socket.fileno() if self._socket else None, request_id)
        response_id, _ = self._receive()
        # Source RCON auth semantics:
        #   SUCCESS  -> server echoes back the original request_id
        #   FAILURE  -> server responds with request_id == -1 (0xFFFFFFFF)
        if response_id != request_id:
            logger.warning("[RCON AUTH] id=%s socket_fileno=%s request_id=%s response_id=%s result=failed", id(self), self._socket.fileno() if self._socket else None, request_id, response_id)
            raise RconAuthError("RCON authentication failed")
        logger.info("[RCON AUTH] id=%s socket_fileno=%s request_id=%s result=success", id(self), self._socket.fileno() if self._socket else None, request_id)
        # Drain trailing SERVERDATA_RESPONSE_VALUE packets with the same request_id.
        # Any other packet is buffered for the next read.
        try:
            while True:
                extra_id, _ = self._receive()
                if extra_id != request_id:
                    self._pending_packet = (extra_id, _)
                    break
        except (RconTimeoutError, RconConnectionError):
            pass

    def _ensure_connected(self) -> None:
        if self._socket is None:
            logger.info("[RCON CONNECT] id=%s socket_fileno=None -> ensure_connected triggered connect", id(self))
            self.connect()
        else:
            logger.debug("[RCON CONNECT] id=%s socket_fileno=%s ensure_connected no-op", id(self), self._socket.fileno())

    def execute_command(self, command: str) -> str:
        """Send a command and return the server response.

        Performs a single automatic reconnect on the first connection/timeout/
        auth failure, since the persistent socket may have dropped silently
        between polls. A second failure is re-raised (it reflects a real state).
        """
        self._last_command = command
        logger.info("[RCON EXECUTE] id=%s socket_fileno=%s command=%r", id(self), self._socket.fileno() if self._socket else None, command)
        attempts = 0
        while attempts < 2:
            try:
                self._ensure_connected()
                request_id = self._send(SERVERDATA_EXECCOMMAND, command)
                logger.debug("[RCON EXECUTE] id=%s socket_fileno=%s request_id=%s command=%r sent=True", id(self), self._socket.fileno() if self._socket else None, request_id, command)
                start = time.time()
                response = self._receive_response(request_id)
                self._last_response_time = time.time() - start
                logger.debug("[RCON EXECUTE] id=%s socket_fileno=%s request_id=%s command=%r response_len=%s", id(self), self._socket.fileno() if self._socket else None, request_id, command, len(response))
                return response
            except (RconConnectionError, RconTimeoutError, RconAuthError):
                if attempts == 0:
                    logger.warning("[RCON RECONNECT] id=%s socket_fileno=%s command=%r attempt=1 detail=connection_lost", id(self), self._socket.fileno() if self._socket else None, command)
                    self._close_socket()
                    attempts += 1
                    continue
                raise

    def get_players(self) -> list[str]:
        """Return the list of online players parsed from /players output."""
        logger.info("[RCON PLAYERS] id=%s socket_fileno=%s already_connected=%s command=/players", id(self), self._socket.fileno() if self._socket else None, self._socket is not None)
        response = self.execute_command("/players")
        return _parse_players(response)

    def save_game(self) -> str:
        return self.execute_command("/save")

    def broadcast_message(self, message: str) -> str:
        return self.execute_command(f"/broadcast {message}")

    # --- low level protocol helpers ---

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send(self, command_type: int, body: str) -> int:
        if self._socket is None:
            raise RconConnectionError("RCON is not connected")
        request_id = self._next_id()
        payload = body.encode("utf-8", errors="replace")
        packet = struct.pack("<ii", request_id, command_type) + payload + b"\x00\x00"
        size = struct.pack("<i", len(packet))
        logger.debug("[RCON EXECUTE] id=%s socket_fileno=%s request_id=%s type=%s body=%r packet_size=%s", id(self), self._socket.fileno() if self._socket else None, request_id, command_type, body, len(packet))
        try:
            self._socket.sendall(size + packet)
        except socket.timeout as exc:
            logger.warning("[RCON TIMEOUT] id=%s socket_fileno=%s request_id=%s detail=send_timeout", id(self), self._socket.fileno() if self._socket else None, request_id)
            raise RconTimeoutError("RCON send timed out") from exc
        except OSError as exc:
            logger.warning("[RCON ERROR] id=%s socket_fileno=%s request_id=%s detail=send_failed error=%s", id(self), self._socket.fileno() if self._socket else None, request_id, exc)
            raise RconConnectionError(f"RCON send failed: {exc}") from exc
        return request_id

    def _receive(self) -> tuple[int, str]:
        if self._socket is None:
            raise RconConnectionError("RCON is not connected")
        if self._pending_packet is not None:
            request_id, body = self._pending_packet
            self._pending_packet = None
            return request_id, body
        try:
            size_data = self._recv_exact(4)
            if len(size_data) < 4:
                logger.warning("[RCON DISCONNECT] id=%s socket_fileno=%s host=%s port=%s detail=closed_while_reading_size", id(self), self._socket.fileno() if self._socket else None, self.host, self.port)
                raise RconConnectionError("RCON connection closed")
            size = struct.unpack("<i", size_data)[0]
            if size <= 0 or size > 65536:
                logger.warning("[RCON ERROR] id=%s socket_fileno=%s host=%s port=%s detail=invalid_packet_size size=%s", id(self), self._socket.fileno() if self._socket else None, self.host, self.port, size)
                raise RconConnectionError("RCON received an invalid packet")
            packet = self._recv_exact(size)
        except socket.timeout as exc:
            logger.warning("[RCON TIMEOUT] id=%s socket_fileno=%s host=%s port=%s detail=receive_timeout", id(self), self._socket.fileno() if self._socket else None, self.host, self.port)
            raise RconTimeoutError("RCON receive timed out") from exc
        except OSError as exc:
            logger.warning("[RCON ERROR] id=%s socket_fileno=%s host=%s port=%s detail=receive_failed error=%s", id(self), self._socket.fileno() if self._socket else None, self.host, self.port, exc)
            raise RconConnectionError(f"RCON receive failed: {exc}") from exc

        request_id, response_type = struct.unpack("<ii", packet[:8])
        body = packet[8:-2].decode("utf-8", errors="replace").rstrip("\x00")
        logger.debug("[RCON EXECUTE] id=%s socket_fileno=%s request_id=%s response_type=%s body=%r", id(self), self._socket.fileno() if self._socket else None, request_id, response_type, body)
        return request_id, body

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            try:
                chunk = self._socket.recv(n - len(buf))
            except socket.timeout as exc:
                raise RconTimeoutError("RCON receive timed out") from exc
            except OSError as exc:
                logger.warning("[RCON ERROR] id=%s socket_fileno=%s host=%s port=%s detail=recv_failed error=%s", id(self), self._socket.fileno() if self._socket else None, self.host, self.port, exc)
                raise RconConnectionError(f"RCON receive failed: {exc}") from exc
            if not chunk:
                break
            buf += chunk
        return buf

    def _receive_response(self, request_id: int) -> str:
        """Collect all response packets for the given request id.

        Factorio 2.x sends responses asynchronously and may fragment them
        across multiple packets. We read all matching packets that are
        immediately available and do not depend on an empty terminator.
        Packets with other request ids are buffered for the next read.
        """
        parts: list[str] = []
        logger.debug("RCON _receive_response start request_id=%s", request_id)
        try:
            while True:
                resp_id, body = self._receive()
                logger.debug("RCON _receive_response received request_id=%s body=%r", resp_id, body)
                if resp_id == request_id:
                    parts.append(body)
                    old_timeout = None
                    try:
                        if self._socket is not None:
                            gettimeout = getattr(self._socket, "gettimeout", None)
                            if gettimeout is not None:
                                old_timeout = gettimeout()
                                self._socket.settimeout(0.05)
                        while True:
                            extra_id, extra_body = self._receive()
                            logger.debug("RCON _receive_response extra request_id=%s body=%r", extra_id, extra_body)
                            if extra_id == request_id:
                                parts.append(extra_body)
                            else:
                                self._pending_packet = (extra_id, extra_body)
                                break
                    except (RconTimeoutError, RconConnectionError):
                        pass
                    finally:
                        if self._socket is not None and old_timeout is not None:
                            try:
                                self._socket.settimeout(old_timeout)
                            except OSError:
                                pass
                    break
                elif resp_id == -1 and not body:
                    break
                else:
                    self._pending_packet = (resp_id, body)
                    break
        except RconConnectionError:
            if not parts:
                raise
        result = "".join(parts).strip()
        logger.debug("RCON _receive_response result request_id=%s response=%r len=%s", request_id, result, len(result))
        return result

    def __enter__(self) -> "RCONService":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()


_rcon_service: Optional[RCONService] = None


def get_rcon_service() -> RCONService:
    """Return the singleton RCON service, creating it if needed."""
    global _rcon_service
    if _rcon_service is None:
        settings = _load_rcon_settings()
        if not settings.get("password"):
            raise RconNotConfiguredError("RCON is not configured")
        _rcon_service = RCONService(
            host=settings["host"],
            port=int(settings["port"]),
            password=settings["password"],
            timeout=int(settings["timeout"]),
        )
    return _rcon_service


def reset_rcon_service() -> None:
    """Reset the singleton RCON service instance."""
    global _rcon_service
    if _rcon_service is not None:
        try:
            _rcon_service.disconnect()
        except Exception:
            pass
        _rcon_service = None


def _parse_players(output: str) -> list[str]:
    """Parse the output of the Factorio /players command.

    Example output:
        Players (2): Player1, Player2
    or:
        Players (1):
          Player1
    """
    if not output:
        return []
    players: list[str] = []
    first = output.splitlines()[0] if output.strip() else ""
    if ":" in first:
        rest = first.split(":", 1)[1]
        inline = [p.strip() for p in rest.split(",") if p.strip()]
        if inline:
            return inline
    for line in output.splitlines()[1:]:
        name = line.strip().lstrip("-").strip()
        if name:
            players.append(name)
    return players


def get_rcon_status() -> dict[str, object]:
    """Return connection status, masking the password."""
    settings = _load_rcon_settings()
    configured = bool(settings.get("password"))
    status: dict[str, object] = {
        "configured": configured,
        "host": settings.get("rcon_host", DEFAULT_RCON_HOST),
        "port": int(settings.get("rcon_port", DEFAULT_RCON_PORT)),
        "connected": False,
        "error": None,
        "connected_since": None,
        "reconnect_count": 0,
        "last_command": None,
        "last_response_time": None,
    }
    if not configured:
        status["error"] = "RCON not configured"
        return status
    try:
        service = get_rcon_service()
        status["connected"] = service.is_connected()
        if not status["connected"]:
            logger.info("[RCON STATUS] id=%s socket_fileno=None host=%s port=%s detail=not_connected_attempting_connect", id(service), service.host, service.port)
            status["connected"] = service.connect()
        else:
            logger.info("[RCON STATUS] id=%s socket_fileno=%s host=%s port=%s detail=already_connected", id(service), service._socket.fileno(), service.host, service.port)
        if status["connected"]:
            status["connected_since"] = service.connected_since
            status["reconnect_count"] = service.reconnect_count
            status["last_command"] = service.last_command
            status["last_response_time"] = service.last_response_time
    except (RconConnectionError, RconTimeoutError, RconAuthError) as exc:
        status["error"] = str(exc)
    except RconNotConfiguredError as exc:
        status["error"] = str(exc)
    return status


def get_rcon_players() -> dict[str, object]:
    """Return the list of online players, masking the password."""
    try:
        service = get_rcon_service()
        players = service.get_players()
        return {
            "connected": True,
            "players": players,
            "player_count": len(players),
            "error": None,
        }
    except RconNotConfiguredError as exc:
        return {"connected": False, "players": [], "player_count": 0, "error": str(exc)}
    except (RconConnectionError, RconTimeoutError, RconAuthError) as exc:
        return {"connected": False, "players": [], "player_count": 0, "error": str(exc)}


def apply_rcon_settings(host: str, port: int, password: str, timeout: int = DEFAULT_RCON_TIMEOUT) -> dict[str, str]:
    """Persist RCON settings into data/settings.json."""
    values = {
        "rcon_host": host or DEFAULT_RCON_HOST,
        "rcon_port": int(port or DEFAULT_RCON_PORT),
        "rcon_password": password,
        "rcon_timeout": int(timeout or DEFAULT_RCON_TIMEOUT),
    }
    result = save_app_settings(values)
    reset_rcon_service()
    return result


def attempt_rcon_connection(host: str, port: int, password: str, timeout: int = DEFAULT_RCON_TIMEOUT) -> dict[str, object]:
    """Attempt a connection with explicit (possibly unpersisted) credentials.

    This opens a SECOND, SHORT-LIVED connection that is disconnected in the
    `finally` block. It intentionally does NOT touch the persistent singleton
    returned by `get_rcon_service()` so that "Test Connection" with temporary
    host/port/password settings does not disturb the live connection state.

    It is only used by the /api/rcon/test endpoint and is the sole place where
    a second RCON instance is created on purpose.
    """
    service = RCONService(host=host or DEFAULT_RCON_HOST, port=int(port or DEFAULT_RCON_PORT), password=password, timeout=int(timeout or DEFAULT_RCON_TIMEOUT))
    try:
        connected = service.connect()
        return {"connected": connected, "error": None}
    except (RconConnectionError, RconTimeoutError, RconAuthError) as exc:
        return {"connected": False, "error": str(exc)}
    finally:
        try:
            service.disconnect()
        except Exception:
            pass
