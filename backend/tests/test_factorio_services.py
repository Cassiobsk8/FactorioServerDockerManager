from pathlib import Path

import json
import pytest

from backend.services import factorio_services_service as fs
from backend.services import settings_service as ss


@pytest.fixture
def factorio_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(fs, "APP_SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(ss, "APP_SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(fs, "PLAYER_DATA_PATH", tmp_path / "player-data.json")
    return tmp_path


def test_load_factorio_services_returns_defaults_when_missing(factorio_paths):
    result = fs.load_factorio_services()
    assert result[fs.FACTORIO_USERNAME_KEY] == ""
    assert result[fs.FACTORIO_TOKEN_KEY] == ""


def test_save_factorio_services_persists_values(factorio_paths):
    result = fs.save_factorio_services("testuser", "token123")
    assert result[fs.FACTORIO_USERNAME_KEY] == "testuser"
    assert result[fs.FACTORIO_TOKEN_KEY] == "toke****"


def test_save_factorio_services_writes_nested_structure(factorio_paths):
    fs.save_factorio_services("testuser", "token123")
    raw = json.loads(fs.APP_SETTINGS_PATH.read_text(encoding="utf-8"))
    assert raw["factorio_services"]["factorio_username"] == "testuser"
    assert raw["factorio_services"]["factorio_service_token"] == "token123"


def test_save_factorio_services_maintains_backward_compatible_flat_keys(factorio_paths):
    fs.save_factorio_services("testuser", "token123")
    raw = json.loads(fs.APP_SETTINGS_PATH.read_text(encoding="utf-8"))
    assert raw["factorio_username"] == "testuser"
    assert raw["factorio_service_token"] == "token123"


def test_load_factorio_services_reads_nested_structure(factorio_paths):
    fs.save_factorio_services("testuser", "token123")
    result = fs.load_factorio_services()
    assert result[fs.FACTORIO_USERNAME_KEY] == "testuser"
    assert result[fs.FACTORIO_TOKEN_KEY] == "token123"


def test_save_factorio_services_masks_token(factorio_paths):
    fs.save_factorio_services("user", "abcdefghijklmnop")
    result = fs.get_factorio_services_status()
    assert result["token_masked"] == "abcd****mnop"
    assert "klmnop" not in result["token_masked"]


def test_get_factorio_services_status_not_configured(factorio_paths):
    fs.save_factorio_services("", "")
    status = fs.get_factorio_services_status()
    assert status["status"] == "not_configured"


def test_get_factorio_services_status_authenticated(factorio_paths):
    fs.save_factorio_services("user", "validtoken123")
    status = fs.get_factorio_services_status()
    assert status["status"] == "authenticated"
    assert status["username"] == "user"
    assert status["token_masked"] == "vali****n123"


def test_get_factorio_services_status_invalid_token(factorio_paths):
    fs.save_factorio_services("user", "token with spaces!")
    status = fs.get_factorio_services_status()
    assert status["status"] == "invalid"


def test_validate_factorio_services_valid(factorio_paths):
    fs.save_factorio_services("user", "validtoken123")
    result = fs.validate_factorio_services()
    assert result["valid"] is True
    assert result["username"] == "user"


def test_validate_factorio_services_missing_username(factorio_paths):
    fs.save_factorio_services("", "validtoken123")
    result = fs.validate_factorio_services()
    assert result["valid"] is False
    assert "username is required" in result["errors"]


def test_validate_factorio_services_missing_token(factorio_paths):
    fs.save_factorio_services("user", "")
    result = fs.validate_factorio_services()
    assert result["valid"] is False
    assert "token is required" in result["errors"]


def test_validate_factorio_services_invalid_token(factorio_paths):
    fs.save_factorio_services("user", "token with spaces!")
    result = fs.validate_factorio_services()
    assert result["valid"] is False
    assert "token must be alphanumeric" in result["errors"]


def test_serialize_factorio_services(factorio_paths):
    fs.save_factorio_services("myuser", "mytoken123")
    result = fs.serialize_factorio_services()
    assert result[fs.PLAYER_DATA_USERNAME_KEY] == "myuser"
    assert result[fs.PLAYER_DATA_TOKEN_KEY] == "mytoken123"


def test_serialize_factorio_services_empty_when_not_configured(factorio_paths):
    result = fs.serialize_factorio_services()
    assert result[fs.PLAYER_DATA_USERNAME_KEY] == ""
    assert result[fs.PLAYER_DATA_TOKEN_KEY] == ""


def test_write_player_data_creates_file(factorio_paths):
    fs.save_factorio_services("myuser", "mytoken123")
    result = fs.write_player_data()
    assert result["written"] is True
    assert fs.PLAYER_DATA_PATH.exists()
    raw = json.loads(fs.PLAYER_DATA_PATH.read_text(encoding="utf-8"))
    assert raw[fs.PLAYER_DATA_USERNAME_KEY] == "myuser"
    assert raw[fs.PLAYER_DATA_TOKEN_KEY] == "mytoken123"


def test_write_player_data_skips_when_not_configured(factorio_paths):
    result = fs.write_player_data()
    assert result["written"] is False
    assert result["reason"] == "not_configured"
    assert not fs.PLAYER_DATA_PATH.exists()


def test_load_player_data_reads_file(factorio_paths):
    fs.save_factorio_services("myuser", "mytoken123")
    fs.write_player_data()
    result = fs.load_player_data()
    assert result[fs.PLAYER_DATA_USERNAME_KEY] == "myuser"
    assert result[fs.PLAYER_DATA_TOKEN_KEY] == "mytoken123"


def test_load_player_data_returns_empty_when_missing(factorio_paths):
    result = fs.load_player_data()
    assert result == {}


def test_token_never_logged_in_production():
    token = "secret-token-12345"
    masked = fs._mask_token(token)
    assert token not in repr(fs)
    assert token not in str(fs.__dict__)
