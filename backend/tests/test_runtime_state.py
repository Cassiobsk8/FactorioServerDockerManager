from pathlib import Path

import pytest

from backend.services.runtime_state_service import (
    RUNTIME_STATE_PATH,
    clear_pending,
    get_runtime_state,
    is_pending,
    mark_pending,
    remove_pending,
)


def _write_state(pending):
    RUNTIME_STATE_PATH.write_text(
        '{"pending": {"' + '", "'.join(pending) + '"}}',
        encoding="utf-8",
    )


def test_initial_state_is_empty():
    RUNTIME_STATE_PATH.unlink(missing_ok=True)
    state = get_runtime_state()
    assert state["has_pending"] is False
    assert state["pending_keys"] == []


def test_mark_pending_adds_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    state = mark_pending("whitelist")
    assert state["has_pending"] is True
    assert "whitelist" in state["pending_keys"]
    assert "whitelist" in state["pending"]
    assert "changed_at" in state["pending"]["whitelist"]
    assert state["pending"]["whitelist"]["label"] == "whitelist"


def test_mark_pending_with_label(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    state = mark_pending("whitelist", "Whitelist")
    assert state["pending"]["whitelist"]["label"] == "Whitelist"


def test_mark_pending_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    mark_pending("whitelist")
    mark_pending("whitelist")
    state = get_runtime_state()
    assert state["pending_keys"] == ["whitelist"]


def test_mark_pending_multiple_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    mark_pending("whitelist", "Whitelist")
    mark_pending("server_settings", "Server Settings")
    state = get_runtime_state()
    assert state["has_pending"] is True
    assert set(state["pending_keys"]) == {"server_settings", "whitelist"}
    assert state["pending"]["whitelist"]["label"] == "Whitelist"
    assert state["pending"]["server_settings"]["label"] == "Server Settings"


def test_remove_pending_removes_single_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    mark_pending("whitelist", "Whitelist")
    mark_pending("server_settings", "Server Settings")
    state = remove_pending("whitelist")
    assert state["has_pending"] is True
    assert "whitelist" not in state["pending_keys"]
    assert "server_settings" in state["pending_keys"]


def test_remove_pending_missing_key_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    mark_pending("whitelist", "Whitelist")
    state = remove_pending("missing")
    assert state["has_pending"] is True
    assert state["pending_keys"] == ["whitelist"]


def test_clear_pending_removes_all_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    mark_pending("whitelist", "Whitelist")
    mark_pending("server_settings", "Server Settings")
    state = clear_pending()
    assert state["has_pending"] is False
    assert state["pending_keys"] == []


def test_is_pending_returns_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    assert is_pending("whitelist") is False


def test_is_pending_returns_true_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.runtime_state_service.RUNTIME_STATE_PATH",
        tmp_path / "runtime_state.json",
    )
    mark_pending("whitelist", "Whitelist")
    assert is_pending("whitelist") is True
    assert is_pending("server_settings") is False
