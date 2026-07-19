from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("fsm.startup")

CommandBuilder = Callable[["StartupBuilder"], None]


class StartupBuilder:
    """Fluent, extensible builder for Factorio server startup command arguments."""

    def __init__(self) -> None:
        self._args: List[str] = []
        self._extensions: List[CommandBuilder] = []

    def add(self, *args: str) -> "StartupBuilder":
        self._args.extend(args)
        return self

    def extend(self, builder: CommandBuilder) -> "StartupBuilder":
        self._extensions.append(builder)
        return self

    def build(self) -> List[str]:
        for extension in self._extensions:
            extension(self)
        return list(self._args)


class RuntimeStartupBuilder(StartupBuilder):
    """Concrete builder for Factorio runtime startup arguments.

    Usage:
        builder = RuntimeStartupBuilder(
            factorio_bin=Path("/factorio/bin/x64/factorio"),
            active_save="MundoTeste.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        builder.with_server_settings(Path("/factorio/config/server-settings.json"))
        builder.with_access_lists(adminlist=Path("..."), banlist=Path("..."), whitelist=Path("..."))
        builder.with_extensions(...)
        cmd = builder.build()
    """

    def __init__(
        self,
        factorio_bin: Path,
        active_save: str,
        rcon_port: str,
        rcon_password: str,
    ) -> None:
        super().__init__()
        self._factorio_bin = factorio_bin
        self._active_save = active_save
        self._rcon_port = rcon_port
        self._rcon_password = rcon_password
        self._server_settings: Optional[Path] = None
        self._adminlist: Optional[Path] = None
        self._banlist: Optional[Path] = None
        self._whitelist: Optional[Path] = None

    def with_server_settings(self, path: Path) -> "RuntimeStartupBuilder":
        self._server_settings = path
        return self

    def with_access_lists(
        self,
        adminlist: Optional[Path] = None,
        banlist: Optional[Path] = None,
        whitelist: Optional[Path] = None,
    ) -> "RuntimeStartupBuilder":
        self._adminlist = adminlist
        self._banlist = banlist
        self._whitelist = whitelist
        return self

    def with_extensions(self, *builders: CommandBuilder) -> "RuntimeStartupBuilder":
        for builder in builders:
            self.extend(builder)
        return self

    def build(self) -> List[str]:
        self._args.clear()
        self._args.append(str(self._factorio_bin))
        self._args.append(f"--start-server={self._active_save}")

        if self._rcon_password:
            self._args.extend([f"--rcon-port={self._rcon_port}", f"--rcon-password={self._rcon_password}"])
        else:
            logger.warning("RCON disabled: password not configured")

        if self._server_settings and self._server_settings.exists():
            self._args.extend([f"--server-settings={self._server_settings}"])

        if self._adminlist and self._adminlist.exists():
            self._args.extend([f"--server-adminlist={self._adminlist}"])

        if self._banlist and self._banlist.exists():
            self._args.extend([f"--server-banlist={self._banlist}"])

        if self._whitelist and self._whitelist.exists():
            self._args.extend([f"--server-whitelist={self._whitelist}", "--use-server-whitelist"])

        for extension in self._extensions:
            extension(self)

        masked_cmd = [
            part if not part.startswith("--rcon-password=") else "--rcon-password=******"
            for part in self._args
        ]
        logger.info("Starting factorio with args: %s", masked_cmd)

        return list(self._args)
