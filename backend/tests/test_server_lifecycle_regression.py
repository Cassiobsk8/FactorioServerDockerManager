import json
import subprocess
import tarfile
from pathlib import Path

import backend.docker_manager as docker_manager
from backend.services import log_manager, runtime_session
from backend.services.factorio_service import (
    FactorioService,
    is_server_installed,
    _clear_pid,
)
from backend.services.save_service import SAVE_DIR, ACTIVE_SAVE_PATH


def _prepare_active_save(tmp_path: Path) -> Path:
    save_dir = tmp_path / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    active_save = save_dir / "MundoTeste.zip"
    active_save.write_text("x", encoding="utf-8")
    ACTIVE_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_SAVE_PATH.write_text(
        json.dumps({"active_save": "MundoTeste.zip"}), encoding="utf-8"
    )
    return active_save


def _prepare_installed_binary(install_dir: Path) -> None:
    bin_dir = install_dir / "bin" / "x64"
    bin_dir.mkdir(parents=True, exist_ok=True)
    factorio_bin = bin_dir / "factorio"
    factorio_bin.write_text("#!/bin/sh\necho sim\n", encoding="utf-8")
    factorio_bin.chmod(0o755)


def test_log_manager_initialization(tmp_path):
    log_manager.reset_log_manager()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")

    manager.ensure()

    for path in (manager.install_log, manager.server_log, manager.crash_log, manager.runtime_log):
        assert path.exists()
    assert manager.console_log_argument().startswith("--console-log=")


def test_start_server_creates_log_and_console_log_arg(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    class FakeProcess:
        pid = 42424

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", lambda *a, **k: FakeProcess()
    )

    service = FactorioService()
    result = service.start_server()

    assert result == "started"
    assert manager.runtime_log.read_text() != ""
    assert "started" in manager.runtime_log.read_text()
    assert manager.server_log.exists()
    assert "--console-log=" in " ".join(docker_manager._factorio_command())


def test_restart_server_runs_without_nameerror(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    class FakeProcess:
        pid = 42425

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", lambda *a, **k: FakeProcess()
    )

    service = FactorioService()
    assert service.start_server() == "started"
    assert service.restart_server() == "started"


def test_start_server_redirects_stdout_stderr_to_log(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    captured = {}

    class FakeProcess:
        pid = 42426

    def fake_popen(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", fake_popen
    )

    service = FactorioService()
    result = service.start_server()

    assert result == "started"
    assert manager.server_log.exists()
    assert captured["kwargs"]["stdout"] is not subprocess.DEVNULL
    assert captured["kwargs"]["stderr"] is subprocess.STDOUT
    assert "--console-log=" in " ".join(docker_manager._factorio_command())


def test_start_server_writes_factorio_output_to_log(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    service = FactorioService()
    result = service.start_server()

    assert result == "started"
    log_content = manager.read_server_log()
    assert "sim" in log_content


def test_start_server_creates_runtime_session(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    class FakeProcess:
        pid = 42427

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", lambda *a, **k: FakeProcess()
    )

    service = FactorioService()
    service.start_server()

    session = runtime_session.get_runtime_session()
    assert session.status == "running"
    assert session.process_id == 42427
    assert session.started_at is not None


def test_stop_server_resets_runtime_session(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    class FakeProcess:
        pid = 42428

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", lambda *a, **k: FakeProcess()
    )

    service = FactorioService()
    service.start_server()

    session = runtime_session.get_runtime_session()
    assert session.status == "running"

    service.stop_server()
    assert session.status == "stopped"
    assert session.started_at is None
    assert session.process_id is None


def test_restart_server_creates_new_runtime_session(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    pid_values = [42429, 42430]

    class FakeProcess:
        def __init__(self, *args, **kwargs):
            self._pid = pid_values.pop(0)

        @property
        def pid(self):
            return self._pid

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", lambda *a, **k: FakeProcess()
    )

    service = FactorioService()
    service.start_server()
    first_started_at = runtime_session.get_runtime_session().started_at

    import time
    time.sleep(0.05)
    service.restart_server()
    second_started_at = runtime_session.get_runtime_session().started_at

    assert runtime_session.get_runtime_session().status == "running"
    assert runtime_session.get_runtime_session().process_id == 42430
    assert second_started_at > first_started_at


def test_clear_installation_resets_runtime_session(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    _prepare_installed_binary(install_dir)
    _prepare_active_save(tmp_path)
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.save_service.SAVE_DIR", tmp_path / "saves")

    class FakeProcess:
        pid = 42431

    monkeypatch.setattr(
        "backend.services.factorio_service.subprocess.Popen", lambda *a, **k: FakeProcess()
    )

    service = FactorioService()
    service.start_server()
    assert runtime_session.get_runtime_session().status == "running"

    from backend.services.factorio_service import clear_installation
    clear_installation()
    assert runtime_session.get_runtime_session().status == "stopped"


def test_install_server_creates_installation(tmp_path, monkeypatch):
    log_manager.reset_log_manager()
    runtime_session.reset_runtime_session()
    _clear_pid()
    manager = log_manager.LogManager(log_dir=tmp_path / "logs")
    monkeypatch.setattr("backend.services.factorio_service.get_log_manager", lambda: manager)

    install_dir = tmp_path / "factorio"
    monkeypatch.setattr(docker_manager, "INSTALL_DIR", install_dir)
    monkeypatch.setattr("backend.services.factorio_service.INSTALL_DIR", install_dir)

    archive = tmp_path / "fake.tar.xz"
    stage = tmp_path / "stage" / "bin" / "x64"
    stage.mkdir(parents=True, exist_ok=True)
    payload = stage / "factorio"
    payload.write_text("#!/bin/sh\necho sim\n", encoding="utf-8")
    with tarfile.open(archive, "w:xz") as tar:
        tar.add(payload, arcname="factorio/bin/x64/factorio")

    service = FactorioService()
    assert service.install_server(archive_path=str(archive)) == "installed"
    assert is_server_installed()
    assert (install_dir / "bin" / "x64" / "factorio").exists()

    log_manager.reset_log_manager()
