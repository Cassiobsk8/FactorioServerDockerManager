from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app import app
from backend.services import world_builder_service
from backend.services.world_builder_service import (
    PREVIEWS_DIR,
    WorldConfig,
    _compute_config_hash,
    validate_factorio_binary,
)
from backend.services.world_config import WorldConfig as WorldConfigDataclass
from backend.routes import world_builder_routes


class DummyWorldConfig(WorldConfigDataclass):
    pass


ELF_MAGIC = b"\x7fELF" + b"\x00" * 100


def _write_fake_elf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ELF_MAGIC)


@pytest.fixture
def client(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_routes, "PREVIEWS_DIR", previews_dir)

    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)

    install_dir = tmp_path / "factorio"
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", install_dir)

    factorio_bin = install_dir / "bin" / "x64" / "factorio"
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        for arg in cmd:
            if arg.startswith("--create="):
                target = Path(arg.split("=", 1)[1])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("zip")
                break
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    yield app.test_client()


def test_options_returns_planets(client):
    response = client.get("/api/world-builder/options?planet=nauvis")
    assert response.status_code == 200
    payload = response.get_json()
    assert "nauvis" in payload["planets"]
    assert "presets" not in payload


def test_preview_generates_and_returns_png(client):
    response = client.post(
        "/api/world-builder/preview",
        json={"world_name": "RouteWorld", "planet": "nauvis"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["preview_hash"] in payload["preview_url"]
    assert payload["preview_url"] == f"/api/world-builder/preview-image/{payload['preview_hash']}.png"


def test_preview_validates_input(client):
    response = client.post(
        "/api/world-builder/preview",
        json={"world_name": "", "planet": "nauvis"},
    )
    assert response.status_code == 400


def test_create_world_returns_201_on_success(client):
    preview_response = client.post(
        "/api/world-builder/preview",
        json={"world_name": "RouteWorld", "planet": "nauvis"},
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.get_json()

    response = client.post(
        "/api/world-builder/create",
        json={
            "world_name": "RouteWorld",
            "planet": "nauvis",
            "preview_hash": preview_payload["preview_hash"],
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["status"] == "created"
    assert payload["save_file"] == "RouteWorld.zip"


def test_create_world_returns_409_when_save_exists(client):
    config = DummyWorldConfig(world_name="Exists", planet="nauvis")
    config_hash = _compute_config_hash(config)
    saves_dir = world_builder_service.SAVE_DIR
    (saves_dir / "Exists.zip").write_text("x")
    (world_builder_service.PREVIEWS_DIR / f"{config_hash}.png").write_text("png")

    response = client.post(
        "/api/world-builder/create",
        json={
            "world_name": "Exists",
            "planet": "nauvis",
            "preview_hash": config_hash,
        },
    )
    assert response.status_code == 409


def test_preview_image_serves_png(client):
    (world_builder_service.PREVIEWS_DIR / "abc123.png").write_text("png")

    response = client.get("/api/world-builder/preview-image/abc123")
    assert response.status_code == 200
    assert response.content_type == "image/png"


def test_preview_image_serves_png_with_extension(client):
    (world_builder_service.PREVIEWS_DIR / "abc123.png").write_text("png")

    response = client.get("/api/world-builder/preview-image/abc123.png")
    assert response.status_code == 200
    assert response.content_type == "image/png"


def test_preview_image_returns_404_when_missing(client):
    response = client.get("/api/world-builder/preview-image/doesnotexist")
    assert response.status_code == 404


def test_preview_image_returns_404_when_missing_with_extension(client):
    response = client.get("/api/world-builder/preview-image/doesnotexist.png")
    assert response.status_code == 404


def test_status_returns_valid_for_elf_binary(client, tmp_path, monkeypatch):
    install_dir = tmp_path / "factorio"
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", install_dir)
    _write_fake_elf(install_dir / "bin" / "x64" / "factorio")

    response = client.get("/api/world-builder/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["valid"] is True
    assert payload["reason"] == "real"


def test_status_returns_invalid_for_python_script(client, tmp_path, monkeypatch):
    install_dir = tmp_path / "factorio"
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", install_dir)
    factorio_bin = install_dir / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    factorio_bin.write_text("#!/usr/bin/env python3\n")

    response = client.get("/api/world-builder/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["valid"] is False
    assert payload["reason"] == "placeholder"
    assert "indisponível" in payload.get("message", "")


def test_status_returns_invalid_when_binary_missing(client, tmp_path, monkeypatch):
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "missing")

    response = client.get("/api/world-builder/status")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["valid"] is False



