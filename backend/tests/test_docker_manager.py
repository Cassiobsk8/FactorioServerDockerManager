import json
import os
from pathlib import Path

import pytest

from backend import docker_manager


def test_is_platform_supported_returns_false_on_windows(monkeypatch):
    monkeypatch.setattr(docker_manager.platform, "system", lambda: "Windows")
    assert docker_manager.is_platform_supported() is False


def test_is_platform_supported_returns_true_on_linux(monkeypatch):
    monkeypatch.setattr(docker_manager.platform, "system", lambda: "Linux")
    assert docker_manager.is_platform_supported() is True


def test_get_save_directory_creates_directory(tmp_path):
    original_save_dir = docker_manager.SAVE_DIR
    docker_manager.SAVE_DIR = tmp_path / "saves"

    try:
        save_dir = docker_manager.get_save_directory()
        assert save_dir.exists()
        assert save_dir.is_dir()
    finally:
        docker_manager.SAVE_DIR = original_save_dir


def test_list_save_files_returns_only_zip_files(tmp_path):
    original_save_dir = docker_manager.SAVE_DIR
    docker_manager.SAVE_DIR = tmp_path / "saves"
    docker_manager.SAVE_DIR.mkdir(parents=True, exist_ok=True)
    (docker_manager.SAVE_DIR / "a.zip").write_text("content")
    (docker_manager.SAVE_DIR / "b.txt").write_text("content")
    (docker_manager.SAVE_DIR / "subdir").mkdir()

    try:
        result = docker_manager.list_save_files()
        assert result == ["a.zip"]
    finally:
        docker_manager.SAVE_DIR = original_save_dir


def test_save_uploaded_file_writes_file(tmp_path):
    original_save_dir = docker_manager.SAVE_DIR
    docker_manager.SAVE_DIR = tmp_path / "saves"

    class DummyUpload:
        def __init__(self, filename, content):
            self.filename = filename
            self._content = content

        def save(self, destination):
            destination.write_bytes(self._content)

    try:
        uploaded = DummyUpload("test.save", b"hello")
        filename = docker_manager.save_uploaded_file(uploaded)
        assert filename == "test.save"
        assert (docker_manager.SAVE_DIR / "test.save").read_bytes() == b"hello"
    finally:
        docker_manager.SAVE_DIR = original_save_dir


def test_save_uploaded_file_rejects_empty_filename():
    with pytest.raises(ValueError, match="Empty file name"):
        docker_manager.save_uploaded_file(type("X", (), {"filename": "", "save": lambda self, dest: None})())


def test_factorio_command_requires_installed_binary(tmp_path, monkeypatch):
    original_install_dir = docker_manager.INSTALL_DIR
    docker_manager.INSTALL_DIR = tmp_path / "factorio"
    try:
        with pytest.raises(RuntimeError, match="Factorio binary not found"):
            docker_manager._factorio_command()
    finally:
        docker_manager.INSTALL_DIR = original_install_dir
