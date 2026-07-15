import json
import tempfile
from pathlib import Path

from backend.docker_manager import load_server_config, save_server_config


def test_load_server_config_uses_defaults(tmp_path):
    config_path = tmp_path / "server_config.json"

    config = load_server_config(config_path)

    assert config["server_name"] == "factorio"
    assert config["server_password"] == "change-me"


def test_save_server_config_persists_values(tmp_path):
    config_path = tmp_path / "server_config.json"

    updated = save_server_config(
        config_path,
        {"server_name": "MyServer", "server_password": "secret123"},
    )

    assert updated["server_name"] == "MyServer"
    assert json.loads(config_path.read_text())["server_password"] == "secret123"
