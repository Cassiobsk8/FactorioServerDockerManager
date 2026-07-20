import json

import pytest

from backend.config import SERVER_SETTINGS_EXAMPLE_PATH, SERVER_SETTINGS_PATH
from backend.services.factorio_service import (
    ServerSettingsExampleMissingError,
    load_server_settings,
)


def test_fresh_install_loads_official_example(tmp_path, monkeypatch):
    # Reproduce a clean install: neither server-settings.json nor the example exist in tmp.
    settings = tmp_path / "server-settings.json"
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_PATH", settings
    )
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_EXAMPLE_PATH",
        tmp_path / "missing-example.json",
    )

    # Without the official example, loading must fail loudly, never produce {}.
    with pytest.raises(ServerSettingsExampleMissingError):
        load_server_settings()

    assert not settings.exists()


def test_fresh_install_with_official_example_present(tmp_path, monkeypatch):
    example = tmp_path / "server-settings.example.json"
    example.write_text(
        json.dumps({"name": "Example", "max_players": 0}), encoding="utf-8"
    )
    settings = tmp_path / "config" / "server-settings.json"
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_PATH", settings
    )
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_EXAMPLE_PATH", example
    )

    # Fresh install: example is copied into server-settings.json and returned.
    result = load_server_settings()
    assert result == {"name": "Example", "max_players": 0}
    assert settings.exists()
    assert json.loads(settings.read_text(encoding="utf-8")) == result


def test_committed_official_example_is_valid_json():
    assert SERVER_SETTINGS_EXAMPLE_PATH.exists()
    data = json.loads(SERVER_SETTINGS_EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "name" in data


def test_load_server_settings_never_returns_empty_object(tmp_path, monkeypatch):
    # Example present, but server-settings.json is empty -> must copy example, not return {}.
    example = tmp_path / "server-settings.example.json"
    example.write_text(
        json.dumps({"name": "Example", "max_players": 0}), encoding="utf-8"
    )
    settings = tmp_path / "server-settings.json"
    settings.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_PATH", settings
    )
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_EXAMPLE_PATH", example
    )

    result = load_server_settings()
    assert result != {}
    assert result == {"name": "Example", "max_players": 0}


def test_example_never_silently_empty_when_missing(tmp_path, monkeypatch):
    settings = tmp_path / "server-settings.json"
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_PATH", settings
    )
    monkeypatch.setattr(
        "backend.services.factorio_service.SERVER_SETTINGS_EXAMPLE_PATH",
        tmp_path / "does-not-exist.example.json",
    )
    with pytest.raises(ServerSettingsExampleMissingError):
        load_server_settings()
    assert not settings.exists()
