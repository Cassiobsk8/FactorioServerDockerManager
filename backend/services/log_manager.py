from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.config import (
    CRASH_LOG_NAME,
    INSTALL_LOG_NAME,
    LOG_DIR,
    RUNTIME_LOG_NAME,
    SERVER_LOG_NAME,
)

logger = logging.getLogger("fsm.logmanager")


class LogManager:
    """Centralizes every log file used by the Server Manager.

    The rest of the application MUST go through this manager and never open a
    log file directly. The server log is produced by the official Factorio
    dedicated server via ``--console-log``; this manager owns the target file
    and exposes typed accessors for every log category.

    Architecture::

        LogManager
          -> install log
          -> server log   (--console-log target, official source)
          -> crash log
          -> runtime log
    """

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self.log_dir = (log_dir or LOG_DIR).resolve()
        self._migrated = False

    # ------------------------------------------------------------------ #
    # Paths (the only place that knows about concrete files)
    # ------------------------------------------------------------------ #
    @property
    def install_log(self) -> Path:
        return self.log_dir / INSTALL_LOG_NAME

    @property
    def server_log(self) -> Path:
        return self.log_dir / SERVER_LOG_NAME

    @property
    def crash_log(self) -> Path:
        return self.log_dir / CRASH_LOG_NAME

    @property
    def runtime_log(self) -> Path:
        return self.log_dir / RUNTIME_LOG_NAME

    def console_log_argument(self) -> str:
        """Return the official ``--console-log=<file>`` argument for the server."""
        self.server_log.parent.mkdir(parents=True, exist_ok=True)
        return f"--console-log={self.server_log}"

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def ensure(self) -> None:
        """Create the log directory and the managed files if missing.

        Safe to call before every read/append; never truncates existing logs.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.install_log, self.server_log, self.crash_log, self.runtime_log):
            self._ensure_file(path)

    def _ensure_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")

    def migrate_existing_installation(self, factorio_root: Optional[Path] = None) -> dict:
        """Migrate a pre-H7 installation to the LogManager layout.

        Old logs (``logs/server.log``, Factorio-generated ``factorio-current.log``
        and ``factorio-previous.log``) are preserved by importing their content
        into the server log instead of being deleted.

        Args:
            factorio_root: override for the Factorio install root legacy
                candidates (used by tests). Defaults to the project's
                ``factorio/`` directory.

        Returns a summary of what was migrated.
        """
        if self._migrated:
            return {"migrated": False, "reason": "already_migrated"}

        self.ensure()

        imported_lines: List[str] = []
        sources: List[str] = []

        if factorio_root is None:
            factorio_root = Path(__file__).resolve().parent.parent.parent / "factorio"

        legacy_candidates = [
            self.log_dir / "factorio-current.log",
            self.log_dir / "factorio-previous.log",
            factorio_root / "factorio-current.log",
            factorio_root / "factorio-previous.log",
        ]

        for candidate in legacy_candidates:
            if candidate.resolve() == self.server_log.resolve():
                continue
            if candidate.exists() and candidate.stat().st_size > 0:
                try:
                    content = candidate.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if content.strip():
                    imported_lines.append(
                        f"--- imported from {candidate.name} ({_now()}) ---"
                    )
                    imported_lines.append(content.rstrip("\n"))
                    sources.append(candidate.name)

        if imported_lines:
            existing = self._read(self.server_log)
            header = "\n".join(imported_lines)
            if existing.strip():
                self.server_log.write_text(
                    existing.rstrip("\n") + "\n" + header + "\n", encoding="utf-8"
                )
            else:
                self.server_log.write_text(header + "\n", encoding="utf-8")

        self._migrated = True
        return {
            "migrated": bool(sources),
            "imported_from": sources,
            "server_log": str(self.server_log),
        }

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #
    def read_install_log(self) -> str:
        return self._read(self.install_log)

    def read_server_log(self) -> str:
        # TEMPORARY DIAGNOSTIC (H7.2A)
        logger.debug("[LOG MANAGER] read_server_log open=%s", self.server_log)
        return self._read(self.server_log)

    def read_crash_log(self) -> str:
        return self._read(self.crash_log)

    def read_runtime_log(self) -> str:
        return self._read(self.runtime_log)

    def read_active_log(self, *, install_in_progress: bool = False) -> str:
        """Return the log appropriate to the current phase.

        During installation the install log is authoritative; otherwise the
        server log (official ``--console-log`` output) is preferred.
        """
        if install_in_progress:
            return self.read_install_log()
        server = self.read_server_log()
        if server.strip():
            return server
        return self.read_install_log()

    def _read(self, path: Path) -> str:
        self.ensure()
        if not path.exists():
            return ""
        # TEMPORARY DIAGNOSTIC (H7.2A)
        content = path.read_text(encoding="utf-8", errors="replace")
        logger.debug("[LOG MANAGER] read_text bytes=%s", len(content.encode("utf-8")))
        return content

    # ------------------------------------------------------------------ #
    # Append
    # ------------------------------------------------------------------ #
    def append_install(self, message: str) -> None:
        self._append(self.install_log, message)

    def append_server(self, message: str) -> None:
        self._append(self.server_log, message)

    def append_crash(self, message: str) -> None:
        self._append(self.crash_log, message)

    def append_runtime(self, message: str) -> None:
        self._append(self.runtime_log, message)

    def _append(self, path: Path, message: str) -> None:
        self.ensure()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip("\n") + "\n")

    # ------------------------------------------------------------------ #
    # Clear
    # ------------------------------------------------------------------ #
    def clear_install_log(self) -> None:
        self._clear(self.install_log)

    def clear_server_log(self) -> None:
        self._clear(self.server_log)

    def clear_active_log(self, *, install_in_progress: bool = False) -> None:
        if install_in_progress:
            self._clear(self.install_log)
        else:
            self._clear(self.server_log)

    def clear_all(self) -> None:
        for path in (self.install_log, self.server_log, self.crash_log, self.runtime_log):
            self._clear(path)

    def _clear(self, path: Path) -> None:
        self.ensure()
        path.write_text("", encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Rotation (future-proofed)
    # ------------------------------------------------------------------ #
    def rotate(self, max_bytes: int = 0, backups: int = 0) -> dict:
        """Rotate managed logs once they exceed ``max_bytes``.

        Size-based rotation is the intended official mechanism. With
        ``max_bytes == 0`` (default) logs are kept as-is (Factorio already
        maintains ``factorio-current.log`` / ``factorio-previous.log``), so this
        is a no-op that documents the future rotation contract.
        """
        rotated: List[str] = []
        if max_bytes <= 0 or backups <= 0:
            return {"rotated": rotated, "reason": "disabled"}

        for path in (self.server_log, self.crash_log, self.runtime_log):
            if not path.exists() or path.stat().st_size <= max_bytes:
                continue
            for index in range(backups - 1, 0, -1):
                older = path.with_suffix(f".{index}.log")
                newer = path.with_suffix(f".{index + 1}.log")
                if older.exists():
                    shutil.move(str(older), str(newer))
            shutil.move(str(path), str(path.with_suffix(".1.log")))
            self._ensure_file(path)
            rotated.append(str(path))

        return {"rotated": rotated}

    def install_logging_handler(self) -> logging.Handler:
        """Attach a Python logging handler that writes to the install log.

        Used during the server installation thread so that app-level log
        records land in the centralized install log.
        """
        self.ensure()
        handler = logging.FileHandler(self.install_log, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(handler)
        return handler

    def remove_logging_handler(self, handler: logging.Handler) -> None:
        logging.getLogger().removeHandler(handler)
        handler.close()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_default_manager: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Return the process-wide default LogManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = LogManager()
    return _default_manager


def reset_log_manager() -> None:
    """Reset the cached manager (used by tests)."""
    global _default_manager
    _default_manager = None
