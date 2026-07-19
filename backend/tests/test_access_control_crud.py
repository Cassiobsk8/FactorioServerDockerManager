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


def test_add_creates_adminlist_file(list_paths):
    result = ac.add_to_list("admins", "Alice")
    assert result["exists"] is True
    assert result["count"] == 1
    assert result["records"] == ["Alice"]
    assert json.loads(list_paths["ADMINLIST_PATH"].read_text()) == {"admins": ["Alice"]}


def test_add_trims_and_dedupes(list_paths):
    ac.add_to_list("whitelist", "Bob")
    # trimmed duplicate is rejected as duplicate
    with pytest.raises(ValueError, match="Duplicate"):
        ac.add_to_list("whitelist", "  Bob  ")
    # distinct name is accepted
    ac.add_to_list("whitelist", "alice")
    status = ac.get_whitelist_status()
    assert status.count == 2
    assert status.records == ["Bob", "alice"]


def test_add_sorts_alphabetically(list_paths):
    for name in ["Charlie", "Alice", "Bob"]:
        ac.add_to_list("whitelist", name)
    assert ac.get_whitelist_status().records == ["Alice", "Bob", "Charlie"]


def test_add_empty_name_raises(list_paths):
    with pytest.raises(ValueError, match="empty"):
        ac.add_to_list("admins", "   ")


def test_add_duplicate_raises(list_paths):
    ac.add_to_list("admins", "Alice")
    with pytest.raises(ValueError, match="Duplicate"):
        ac.add_to_list("admins", "Alice")


def test_remove_existing(list_paths):
    ac.add_to_list("banlist", "Eve")
    ac.add_to_list("banlist", "Frank")
    result = ac.remove_from_list("banlist", "Eve")
    assert result["count"] == 1
    assert result["records"] == ["Frank"]


def test_remove_missing_raises(list_paths):
    ac.add_to_list("whitelist", "Alice")
    with pytest.raises(ValueError, match="not found"):
        ac.remove_from_list("whitelist", "Ghost")


def test_remove_last_entry_deletes_file(list_paths):
    ac.add_to_list("whitelist", "Alice")
    ac.remove_from_list("whitelist", "Alice")
    assert not list_paths["WHITELIST_PATH"].exists()
    assert ac.get_whitelist_status().exists is False


def test_unknown_list_key_raises(list_paths):
    with pytest.raises(ValueError, match="Unknown"):
        ac.add_to_list("mods", "x")


def test_enable_whitelist_creates_file(list_paths):
    assert not list_paths["WHITELIST_PATH"].exists()
    result = ac.enable_whitelist()
    assert result["exists"] is True
    assert result["count"] == 0
    assert result["records"] == []
    assert list_paths["WHITELIST_PATH"].exists()
    assert json.loads(list_paths["WHITELIST_PATH"].read_text()) == []


def test_enable_whitelist_idempotent(list_paths):
    list_paths["WHITELIST_PATH"].write_text("[]")
    result = ac.enable_whitelist()
    assert result["exists"] is True
    assert result["count"] == 0
    assert json.loads(list_paths["WHITELIST_PATH"].read_text()) == []


def test_disable_whitelist_removes_file(list_paths):
    list_paths["WHITELIST_PATH"].write_text("[]")
    assert list_paths["WHITELIST_PATH"].exists()
    result = ac.disable_whitelist()
    assert result["exists"] is False
    assert result["count"] == 0
    assert not list_paths["WHITELIST_PATH"].exists()


def test_disable_whitelist_idempotent(list_paths):
    result = ac.disable_whitelist()
    assert result["exists"] is False
    assert result["count"] == 0
    assert not list_paths["WHITELIST_PATH"].exists()
