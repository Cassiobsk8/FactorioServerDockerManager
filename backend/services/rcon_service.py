from __future__ import annotations

import logging

logger = logging.getLogger("fsm.rcon")


class RconNotImplementedError(Exception):
    pass


def send_rcon_command(command: str) -> str:
    raise RconNotImplementedError("RCON service is not yet implemented")
