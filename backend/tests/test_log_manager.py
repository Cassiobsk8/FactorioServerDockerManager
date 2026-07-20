from pathlib import Path

from backend.services import log_manager
from backend.services.log_manager import LogManager


def _fresh_manager(tmp_path: Path) -> LogManager:
    log_manager.reset_log_manager()
    return LogManager(log_dir=tmp_path / "logs")


def test_ensure_creates_all_log_files(tmp_path):
    manager = _fresh_manager(tmp_path)

    manager.ensure()

    for path in (manager.install_log, manager.server_log, manager.crash_log, manager.runtime_log):
        assert path.exists()
        assert path.read_text() == ""


def test_server_log_is_console_log_target(tmp_path):
    manager = _fresh_manager(tmp_path)

    arg = manager.console_log_argument()

    assert arg.startswith("--console-log=")
    assert arg.endswith(str(manager.server_log))


def test_ensure_does_not_truncate_existing_content(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.ensure()
    manager.append_server("existing line")

    manager.ensure()

    assert "existing line" in manager.read_server_log()


def test_read_returns_content(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.ensure()
    manager.append_server("alpha")
    manager.append_server("beta")

    content = manager.read_server_log()

    assert content == "alpha\nbeta\n"


def test_read_missing_file_returns_empty(tmp_path):
    manager = _fresh_manager(tmp_path)

    assert manager.read_server_log() == ""


def test_append_creates_file_when_missing(tmp_path):
    manager = _fresh_manager(tmp_path)

    manager.append_install("install event")

    assert manager.install_log.exists()
    assert manager.read_install_log() == "install event\n"


def test_append_is_idempotent_across_categories(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.append_crash("boom")
    manager.append_runtime("tick")

    assert manager.read_crash_log() == "boom\n"
    assert manager.read_runtime_log() == "tick\n"


def test_clear_active_log_prefers_server_when_not_installing(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.append_server("live")
    manager.append_install("setup")

    manager.clear_active_log(install_in_progress=False)

    assert manager.read_server_log() == ""
    assert manager.read_install_log() == "setup\n"


def test_clear_active_log_prefers_install_while_installing(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.append_server("live")
    manager.append_install("setup")

    manager.clear_active_log(install_in_progress=True)

    assert manager.read_install_log() == ""
    assert manager.read_server_log() == "live\n"


def test_read_active_log_falls_back_to_install(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.ensure()
    manager.append_install("only install")

    assert manager.read_active_log(install_in_progress=False) == "only install\n"


def test_rotate_disabled_is_noop(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.append_server("data")

    result = manager.rotate(max_bytes=0, backups=0)

    assert result["reason"] == "disabled"
    assert manager.read_server_log() == "data\n"


def test_rotate_moves_oversized_log(tmp_path):
    manager = _fresh_manager(tmp_path)
    manager.append_server("x" * 100)
    for path in (manager.server_log,):
        path.write_text("y" * 50, encoding="utf-8")

    result = manager.rotate(max_bytes=10, backups=1)

    assert str(manager.server_log) in result["rotated"]
    assert manager.server_log.exists()
    assert manager.server_log.with_suffix(".1.log").exists()


def test_migrate_imports_factorio_generated_logs(tmp_path):
    factorio_root = tmp_path / "factorio"
    factorio_root.mkdir()
    (factorio_root / "factorio-current.log").write_text("legacy runtime output\n", encoding="utf-8")

    manager = _fresh_manager(tmp_path)
    summary = manager.migrate_existing_installation(factorio_root=factorio_root)

    assert summary["migrated"] is True
    assert "factorio-current.log" in summary["imported_from"]
    assert "legacy runtime output" in manager.read_server_log()
    assert "imported from" in manager.read_server_log()


def test_migrate_preserves_existing_server_log(tmp_path):
    factorio_root = tmp_path / "factorio"
    factorio_root.mkdir()
    (factorio_root / "factorio-current.log").write_text("old runtime\n", encoding="utf-8")

    manager = _fresh_manager(tmp_path)
    manager.ensure()
    manager.append_server("official content")

    summary = manager.migrate_existing_installation(factorio_root=factorio_root)

    assert "old runtime" in manager.read_server_log()
    assert "official content" in manager.read_server_log()
    assert "factorio-current.log" in summary["imported_from"]


def test_migrate_is_idempotent(tmp_path):
    factorio_root = tmp_path / "factorio"
    factorio_root.mkdir()
    (factorio_root / "factorio-previous.log").write_text("first\n", encoding="utf-8")

    manager = _fresh_manager(tmp_path)
    first = manager.migrate_existing_installation(factorio_root=factorio_root)
    second = manager.migrate_existing_installation(factorio_root=factorio_root)

    assert first["migrated"] is True
    assert second["migrated"] is False
    assert second["reason"] == "already_migrated"


def test_migrate_noop_when_nothing_legacy(tmp_path):
    manager = _fresh_manager(tmp_path)
    summary = manager.migrate_existing_installation(factorio_root=tmp_path / "factorio")

    assert summary["migrated"] is False
    assert summary["imported_from"] == []


def test_default_manager_singleton():
    log_manager.reset_log_manager()
    a = log_manager.get_log_manager()
    b = log_manager.get_log_manager()
    assert a is b
    log_manager.reset_log_manager()


def test_read_server_log_rereads_physical_file_each_call(tmp_path):
    # REGRESSION (H7.2 / items #4 #5): each GET to /logs/data must read the
    # physical file fresh. Mutating the file outside the manager must be
    # reflected by the very next read_server_log() call (no in-memory cache,
    # no persistent read handle).
    manager = _fresh_manager(tmp_path)
    manager.ensure()
    manager.append_server("alpha\n")

    assert manager.read_server_log() == "alpha\n"

    # Simulate the Factorio server appending directly to the file on disk.
    manager.server_log.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    assert manager.read_server_log() == "alpha\nbeta\ngamma\n"


def test_read_active_log_rereads_physical_file_each_call(tmp_path):
    # read_active_log() (used by /logs/data and /api/logs) must also re-read
    # the file instead of serving any cached content.
    manager = _fresh_manager(tmp_path)
    manager.ensure()
    manager.append_server("first\n")

    assert manager.read_active_log() == "first\n"

    manager.server_log.write_text("first\nsecond\n", encoding="utf-8")

    assert manager.read_active_log() == "first\nsecond\n"
