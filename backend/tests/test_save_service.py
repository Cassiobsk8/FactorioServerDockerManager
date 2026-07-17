import json
from pathlib import Path

import pytest

from backend.services import save_service
from backend.config import SAVE_DIR, ACTIVE_SAVE_PATH


def test_list_save_files_returns_only_zip_files(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "SAVE_DIR", tmp_path / "saves")
    (tmp_path / "saves").mkdir(parents=True, exist_ok=True)
    (tmp_path / "saves" / "a.zip").write_text("content")
    (tmp_path / "saves" / "b.txt").write_text("content")
    (tmp_path / "saves" / "subdir").mkdir()

    result = save_service.list_save_files()
    assert result == ["a.zip"]


def test_select_save_persists_active_save(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "SAVE_DIR", tmp_path / "saves")
    active_save_path = tmp_path / "active_save.json"
    monkeypatch.setattr(save_service, "ACTIVE_SAVE_PATH", active_save_path)
    (tmp_path / "saves").mkdir(parents=True, exist_ok=True)
    (tmp_path / "saves" / "world.zip").write_text("content")

    result = save_service.select_save("world.zip")
    assert result == {"active_save": "world.zip"}
    assert save_service.get_active_save() == "world.zip"
    assert json.loads(active_save_path.read_text())["active_save"] == "world.zip"


def test_get_active_save_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "ACTIVE_SAVE_PATH", tmp_path / "missing.json")
    assert save_service.get_active_save() is None


def test_delete_save_blocks_active_save(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "SAVE_DIR", tmp_path / "saves")
    monkeypatch.setattr(save_service, "ACTIVE_SAVE_PATH", tmp_path / "active_save.json")
    (tmp_path / "saves").mkdir(parents=True, exist_ok=True)
    (tmp_path / "saves" / "active.zip").write_text("content")
    save_service.select_save("active.zip")

    with pytest.raises(ValueError, match="Cannot delete the active save"):
        save_service.delete_save("active.zip")


def test_create_save_generates_zip_and_selects_it(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "SAVE_DIR", tmp_path / "saves")
    monkeypatch.setattr(save_service, "ACTIVE_SAVE_PATH", tmp_path / "active_save.json")
    (tmp_path / "saves").mkdir(parents=True, exist_ok=True)

    factorio_dir = tmp_path / "factorio"
    factorio_bin = factorio_dir / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    factorio_bin.write_text("#!/bin/bash\n")
    factorio_bin.chmod(0o755)

    fake_module_file = tmp_path / "backend" / "services" / "save_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(save_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        for arg in cmd:
            if arg.startswith("--create="):
                target = Path(arg.split("=", 1)[1])
                target.write_text("mock")
                break

    monkeypatch.setattr(save_service.subprocess, "run", mock_run)

    result = save_service.create_save("new_world", seed="1234")
    assert result["name"] == "new_world.zip"
    assert result["active"] is True
    assert (tmp_path / "saves" / "new_world.zip").exists()
