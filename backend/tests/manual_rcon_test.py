#!/usr/bin/env python3
"""Manual RCON test script for Factorio 2.x investigation."""
from __future__ import annotations

import logging
import socket
import struct

from backend.services.rcon_service import (
    RCONService,
    RconAuthError,
    RconConnectionError,
    RconTimeoutError,
)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("fsm.rcon.manual")


def _pack(request_id: int, response_type: int, body: str) -> bytes:
    payload = struct.pack("<ii", request_id, response_type) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


def test_manual_rcon():
    service = RCONService(host="127.0.0.1", port=27015, password="868868", timeout=5)
    try:
        logger.info("=== Connecting ===")
        connected = service.connect()
        logger.info("Connected: %s", connected)

        commands = ["/help", "/players", "/server-save", "help", "players"]
        for cmd in commands:
            logger.info("=== Executing: %r ===", cmd)
            try:
                result = service.execute_command(cmd)
                logger.info("Result for %r: %r (len=%s)", cmd, result, len(result))
            except (RconConnectionError, RconTimeoutError, RconAuthError) as exc:
                logger.error("Error for %r: %s", cmd, exc)
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
    finally:
        service.disconnect()


if __name__ == "__main__":
    test_manual_rcon()
