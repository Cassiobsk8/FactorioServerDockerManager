from pathlib import Path

import pytest

from backend.services import startup_validation_service as sv
from backend.services import settings_service as ss
from backend.services import save_service
from backend.services import access_control_service as ac


@pytest.fixture
def validation_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "SERVER_SETTINGS_PATH", tmp_path / "server-settings.json")
    monkeypatch.setattr(sv, "ADMINLIST_PATH", tmp_path / "server-adminlist.json")
    monkeypatch.setattr(sv, "BANLIST_PATH", tmp_path / "server-banlist.json")
    monkeypatch.setattr(sv, "WHITELIST_PATH", tmp_path / "server-whitelist.json")
    monkeypatch.setattr(ss, "APP_SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(save_service, "ACTIVE_SAVE_PATH", tmp_path / "active_save.json")
    monkeypatch.setattr(save_service, "SAVE_DIR", tmp_path / "saves")
    return tmp_path


def test_valid_startup(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    result = sv.validate_startup()
    assert result["valid"] is True
    assert result["errors"] == []


def test_no_active_save(validation_paths):
    (validation_paths / "server-settings.json").write_text("{}")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "no_active_save" for e in result["errors"])


def test_server_settings_missing(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "server_settings_missing" for e in result["errors"])


def test_rcon_password_missing(validation_paths):
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "rcon_password_missing" for e in result["errors"])


def test_whitelist_invalid_json(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    (validation_paths / "server-whitelist.json").write_text("{invalid}", encoding="utf-8")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "whitelist_invalid" for e in result["errors"])


def test_whitelist_not_list(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    (validation_paths / "server-whitelist.json").write_text("{}", encoding="utf-8")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "whitelist_invalid" for e in result["errors"])


def test_adminlist_invalid_json(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    (validation_paths / "server-adminlist.json").write_text("{invalid}", encoding="utf-8")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "adminlist_invalid" for e in result["errors"])


def test_banlist_invalid_json(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    (validation_paths / "server-banlist.json").write_text("{invalid}", encoding="utf-8")
    result = sv.validate_startup()
    assert result["valid"] is False
    assert any(e["code"] == "banlist_invalid" for e in result["errors"])


def test_optional_lists_absent_are_valid(validation_paths, monkeypatch):
    monkeypatch.setattr(ss, "load_app_settings", lambda: {"rcon_password": "secret"})
    (validation_paths / "server-settings.json").write_text("{}")
    save_service.ACTIVE_SAVE_PATH.write_text(
        '{"active_save": "test.zip"}', encoding="utf-8"
    )
    save_dir = validation_paths / "saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "test.zip").write_text("")
    result = sv.validate_startup()
    assert result["valid"] is True
