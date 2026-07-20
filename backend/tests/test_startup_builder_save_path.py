from pathlib import Path

from backend.services.startup_builder import RuntimeStartupBuilder, StartupConfiguration


def _base(tmp_path: Path):
    return dict(
        factorio_bin=tmp_path / "factorio",
        active_save=tmp_path / "data" / "saves" / "MundoTeste.zip",
        rcon_port="27015",
        rcon_password="secret",
    )


def test_start_server_uses_absolute_save_path():
    cmd = RuntimeStartupBuilder(**_base(Path("/app"))).build()
    assert cmd[1] == "--start-server=/app/data/saves/MundoTeste.zip"


def test_start_server_save_path_preserved_when_relative_dir():
    # Saves live outside the Factorio dir (data/saves), so absolute path must be used.
    cmd = RuntimeStartupBuilder(**_base(Path("/srv/app"))).build()
    assert cmd[1] == "--start-server=/srv/app/data/saves/MundoTeste.zip"
    assert cmd[1] != "--start-server=MundoTeste.zip"


def test_start_server_save_path_is_absolute():
    tmp_path = Path("/var/lib/fsm")
    config = StartupConfiguration(
        factorio_bin=tmp_path / "factorio",
        active_save=tmp_path / "data" / "saves" / "MundoTeste.zip",
        rcon_port="27015",
        rcon_password="secret",
    )
    cmd = RuntimeStartupBuilder(config).build()
    start = cmd[1]
    assert start.startswith("--start-server=")
    save = start[len("--start-server="):]
    assert Path(save).is_absolute()
