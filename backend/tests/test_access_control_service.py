from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services import access_control_service as ac


@pytest.fixture
def list_paths(tmp_path, monkeypatch):
    paths = {
        "ADMINLIST_PATH": tmp_path / "server-adminlist.json",
        "WHITELIST_PATH": tmp_path / "server-whitelist.json",
        "BANLIST_PATH": tmp_path / "server-banlist.json",
    }
    for name, path in paths.items():
        monkeypatch.setattr(ac, name, path)
    return paths


def test_missing_files_are_valid_absent(list_paths):
    status = ac.get_access_control_status()
    for key in ("admins", "whitelist", "banlist"):
        assert status[key]["exists"] is False
        assert status[key]["valid"] is True
        assert status[key]["count"] == 0
        assert status[key]["error"] is None


def test_adminlist_object_form(list_paths):
    list_paths["ADMINLIST_PATH"].write_text(json.dumps({"admins": ["Alice", "Bob"]}))
    result = ac.get_adminlist_status()
    assert result.exists is True
    assert result.valid is True
    assert result.count == 2
    assert result.records == ["Alice", "Bob"]


def test_whitelist_array_form(list_paths):
    list_paths["WHITELIST_PATH"].write_text(json.dumps(["Carol", "Dave"]))
    result = ac.get_whitelist_status()
    assert result.exists is True
    assert result.valid is True
    assert result.count == 2


def test_banlist_object_form_with_mixed_entries(list_paths):
    list_paths["BANLIST_PATH"].write_text(
        json.dumps({"bans": [{"username": "Eve"}, "Frank"]})
    )
    result = ac.get_banlist_status()
    assert result.exists is True
    assert result.valid is True
    assert result.count == 2
    assert result.records == ["Eve", "Frank"]


def test_invalid_json_is_flagged(list_paths):
    list_paths["ADMINLIST_PATH"].write_text("{not valid json")
    result = ac.get_adminlist_status()
    assert result.exists is True
    assert result.valid is False
    assert result.error is not None


def test_adminlist_wrong_shape_is_invalid(list_paths):
    list_paths["ADMINLIST_PATH"].write_text(json.dumps({"admins": "not-a-list"}))
    result = ac.get_adminlist_status()
    assert result.valid is False
