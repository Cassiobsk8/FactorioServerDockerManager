from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("fsm.runtime.session")


class RuntimeSession:
    """Ephemeral runtime information for the current server session.

    This state is intentionally in-memory only. It is reset on application
    restart and must not be persisted to disk.
    """

    def __init__(self) -> None:
        self.started_at: Optional[datetime] = None
        self.status: str = "stopped"
        self.process_id: Optional[int] = None
        self.last_restart_reason: Optional[str] = None

    def start(self, pid: int, reason: Optional[str] = None) -> None:
        self.started_at = datetime.now(timezone.utc)
        self.process_id = pid
        self.status = "running"
        self.last_restart_reason = reason
        logger.info("Runtime session started pid=%s", pid)

    def stop(self) -> None:
        self.started_at = None
        self.process_id = None
        self.status = "stopped"
        self.last_restart_reason = None
        logger.info("Runtime session stopped")

    def restart(self, pid: int, reason: Optional[str] = None) -> None:
        self.stop()
        self.start(pid, reason)

    def get_uptime(self) -> int:
        if self.started_at is None or self.status != "running":
            return 0
        return int((datetime.now(timezone.utc) - self.started_at).total_seconds())

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "uptime_seconds": self.get_uptime(),
            "process_id": self.process_id,
            "last_restart_reason": self.last_restart_reason,
        }


_default_session: Optional[RuntimeSession] = None


def get_runtime_session() -> RuntimeSession:
    global _default_session
    if _default_session is None:
        _default_session = RuntimeSession()
    return _default_session


def reset_runtime_session() -> None:
    global _default_session
    _default_session = None
    logger.info("Runtime session reset")
