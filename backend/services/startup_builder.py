from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger("fsm.startup")

CommandBuilder = Callable[["RuntimeStartupBuilder"], None]


@dataclass
class StartupConfiguration:
    """Centralized configuration for Factorio server startup."""

    factorio_bin: Path
    active_save: Path
    rcon_port: str
    rcon_password: str
    port: Optional[str] = None
    bind: Optional[str] = None
    rcon_bind: Optional[str] = None
    server_id: Optional[Path] = None
    use_authserver_bans: bool = False
    server_settings: Optional[Path] = None
    adminlist: Optional[Path] = None
    banlist: Optional[Path] = None
    whitelist: Optional[Path] = None
    console_log: Optional[Path] = None


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
        config = StartupConfiguration(
            factorio_bin=Path("/factorio/bin/x64/factorio"),
            active_save="MundoTeste.zip",
            rcon_port="27015",
            rcon_password="secret",
            port="34197",
            bind="0.0.0.0",
            rcon_bind="127.0.0.1",
            server_id=Path("/factorio/config/server-id.json"),
            use_authserver_bans=True,
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
    """

    def __init__(self, config: Optional[StartupConfiguration] = None, **kwargs) -> None:
        super().__init__()
        if config is not None:
            self._config = config
        else:
            self._config = StartupConfiguration(**kwargs)

    def build(self) -> List[str]:
        self._args.clear()
        config = self._config

        self._args.append(str(config.factorio_bin))
        self._args.append(f"--start-server={config.active_save}")

        if config.port:
            self._args.append(f"--port={config.port}")

        if config.bind:
            self._args.append(f"--bind={config.bind}")

        if config.rcon_password:
            self._args.extend([f"--rcon-port={config.rcon_port}", f"--rcon-password={config.rcon_password}"])
            if config.rcon_bind:
                self._args.append(f"--rcon-bind={config.rcon_bind}")
        else:
            logger.warning("RCON disabled: password not configured")

        if config.server_id and config.server_id.exists():
            self._args.append(f"--server-id={config.server_id}")

        if config.use_authserver_bans:
            self._args.append("--use-authserver-bans")

        if config.server_settings and config.server_settings.exists():
            self._args.extend([f"--server-settings={config.server_settings}"])

        if config.adminlist and config.adminlist.exists():
            self._args.extend([f"--server-adminlist={config.adminlist}"])

        if config.banlist and config.banlist.exists():
            self._args.extend([f"--server-banlist={config.banlist}"])

        if config.whitelist and config.whitelist.exists():
            self._args.extend([f"--server-whitelist={config.whitelist}", "--use-server-whitelist"])

        if config.console_log is not None:
            self._args.append(f"--console-log={config.console_log}")

        for extension in self._extensions:
            extension(self)

        masked_cmd = [
            part if not part.startswith("--rcon-password=") else "--rcon-password=******"
            for part in self._args
        ]
        logger.info("Starting factorio with args: %s", masked_cmd)

        return list(self._args)
