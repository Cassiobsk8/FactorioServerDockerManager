from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

from backend.config import BASE_DIR, SAVE_DIR
from backend.services import world_builder_service
from backend.services.world_builder_service import (
    _cleanup_tempdir,
    _compute_config_hash,
    _move_generated_file,
    _run_factorio,
    _write_map_gen_settings,
    _write_map_settings,
    create_world,
    generate_preview,
    list_planets,
    PREVIEWS_DIR,
    WorldConfig,
    validate_factorio_binary,
)
from backend.services.world_config import WorldConfig as WorldConfigDataclass


class DummyWorldConfig(WorldConfigDataclass):
    pass


ELF_MAGIC = b"\x7fELF" + b"\x00" * 100


def _write_fake_elf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ELF_MAGIC)


def test_list_planets_returns_default_planets():
    assert list_planets() == ["nauvis", "vulcanus", "fulgora", "gleba", "aquilo"]

def test_compute_config_hash_is_deterministic():
    config = DummyWorldConfig(world_name="Mundo", planet="nauvis")
    first = _compute_config_hash(config)
    second = _compute_config_hash(config)
    assert first == second
    assert len(first) == 64


def test_compute_config_hash_differs_on_seed():
    config_a = DummyWorldConfig(world_name="Mundo", seed="1", random_seed=False)
    config_b = DummyWorldConfig(world_name="Mundo", seed="2", random_seed=False)
    assert _compute_config_hash(config_a) != _compute_config_hash(config_b)


def test_validate_requires_world_name():
    config = DummyWorldConfig(world_name="")
    assert "world_name is required" in config.validate()

    config = DummyWorldConfig(world_name="   ")
    assert "world_name is required" in config.validate()


def test_validate_rejects_unknown_planet():
    config = DummyWorldConfig(world_name="ok", planet="mars")
    errors = config.validate()
    assert any("unsupported planet" in e for e in errors)


def test_generate_preview_creates_file_and_returns_url(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    result = generate_preview(config)

    assert result["status"] == "ready"
    assert result["preview_hash"] in result["preview_url"]
    assert (previews_dir / f"{result['preview_hash']}.png").exists()


def test_generate_preview_returns_existing_without_regen(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    (tmp_path / "factorio" / "bin" / "x64").mkdir(parents=True, exist_ok=True)
    _write_fake_elf(tmp_path / "factorio" / "bin" / "x64" / "factorio")

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    config_hash = _compute_config_hash(config)
    (previews_dir / f"{config_hash}.png").write_text("png")

    run_called = False

    def mock_run(*args, **kwargs):
        nonlocal run_called
        run_called = True
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    result = generate_preview(config)
    assert result["status"] == "ready"
    assert not run_called


def test_create_world_creates_save_and_returns_metadata(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        for arg in cmd:
            if arg.startswith("--create="):
                target = Path(arg.split("=", 1)[1])
                target.write_text("zip")
                break
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="NewWorld", planet="nauvis")
    preview = generate_preview(config)
    result = create_world(config, preview["preview_hash"])

    assert result["status"] == "created"
    assert result["save_file"] == "NewWorld.zip"
    assert (saves_dir / "NewWorld.zip").exists()


def test_create_world_conflicts_on_existing_save(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    (saves_dir / "Exists.zip").write_text("x")

    config = DummyWorldConfig(world_name="Exists", planet="nauvis")
    config_hash = _compute_config_hash(config)
    (previews_dir / f"{config_hash}.png").write_text("png")

    with pytest.raises(FileExistsError, match="Save already exists"):
        create_world(config, config_hash)


def test_create_world_rejects_mismatched_preview_hash(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    (tmp_path / "factorio" / "bin" / "x64").mkdir(parents=True, exist_ok=True)
    _write_fake_elf(tmp_path / "factorio" / "bin" / "x64" / "factorio")

    config = DummyWorldConfig(world_name="Mundo", planet="nauvis")
    with pytest.raises(ValueError, match="Preview hash does not match"):
        create_world(config, preview_hash="bad-hash")


def test_validate_factorio_binary_accepts_elf_magic(tmp_path, monkeypatch):
    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    _write_fake_elf(factorio_bin)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    result = validate_factorio_binary()
    assert result["valid"] is True
    assert result["reason"] == "real"


def test_validate_factorio_binary_rejects_python_script(tmp_path, monkeypatch):
    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    factorio_bin.write_text("#!/usr/bin/env python3\n")

    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    result = validate_factorio_binary()
    assert result["valid"] is False
    assert result["reason"] == "placeholder"
    assert "indisponível" in result.get("message", "")


def test_validate_factorio_binary_rejects_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "missing")

    with pytest.raises(RuntimeError, match="Factorio binary not found"):
        validate_factorio_binary()


def test_generate_preview_uses_official_parameters(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    captured_cmd = []

    def mock_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(
        world_name="TestWorld",
        seed="12345",
        random_seed=False,
        planet="nauvis",
    )
    generate_preview(config)

    assert captured_cmd[0] == str(factorio_bin)
    assert "--generate-map-preview" in captured_cmd
    assert "preview.png" in captured_cmd
    assert any(arg.startswith("--map-gen-seed=") for arg in captured_cmd)
    assert "--map-preview-size" in captured_cmd
    assert "1024" in captured_cmd
    assert any(arg.startswith("--map-preview-planet=") for arg in captured_cmd)


def test_generate_preview_with_custom_settings(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    captured_cmd = []

    def mock_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(
        world_name="TestWorld",
        seed="42",
        random_seed=False,
        planet="vulcanus",
        settings={"water": 0.5},
        map_settings={"difficulty_settings": {"recipe_difficulty": 2}},
    )
    generate_preview(config)

    assert "--generate-map-preview" in captured_cmd
    assert any(arg.startswith("--map-gen-settings=") for arg in captured_cmd)
    assert any(arg.startswith("--map-settings=") for arg in captured_cmd)
    assert any(arg.startswith("--map-preview-planet=") for arg in captured_cmd)
    assert any(arg.startswith("--map-gen-seed=") for arg in captured_cmd)


def test_create_world_uses_official_parameters(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    captured_cmd = []

    def mock_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        for arg in cmd:
            if arg.startswith("--create="):
                target = Path(arg.split("=", 1)[1])
                target.write_text("zip")
                break
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(
        world_name="NewWorld",
        seed="999",
        random_seed=False,
        planet="nauvis",
    )
    preview = generate_preview(config)
    create_world(config, preview["preview_hash"])

    assert any(arg.startswith("--create=") for arg in captured_cmd)
    assert "--map-gen-seed=999" in captured_cmd
    assert any(arg.startswith("--map-gen-settings=") for arg in captured_cmd) is False


def test_generate_preview_handles_executable_error(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="Some Factorio error",
        )

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError, match="Failed to generate preview"):
        generate_preview(config)


def test_generate_preview_diagnostics_on_missing_png(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "factorio-current.log").write_text("log")
        (cwd / "map-gen-settings.json").write_text("{}")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError) as exc_info:
        generate_preview(config)

    message = str(exc_info.value)
    assert "preview.png existe: False" in message
    assert "PNGs encontrados: nenhum" in message
    assert "factorio-current.log" in message
    assert "map-gen-settings.json" in message
    assert "Comando:" in message
    assert "cwd:" in message
    assert "return code:" in message


def test_generate_preview_diagnostics_lists_any_png(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "other.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError) as exc_info:
        generate_preview(config)

    message = str(exc_info.value)
    assert "PNGs encontrados: ['other.png']" in message
    assert "other.png" in message


def test_generate_preview_diagnostics_on_process_error(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "factorio-current.log").write_text("log")
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="Some Factorio error",
        )

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError) as exc_info:
        generate_preview(config)

    message = str(exc_info.value)
    assert "Failed to generate preview" in message
    assert "Comando:" in message
    assert "cwd:" in message
    assert "stderr: Some Factorio error" in message
    assert "return code: 1" in message
    assert "factorio-current.log" in message
    assert "arquivos no diretório temporário:" in message
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="Some Factorio error",
        )

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    config_hash = _compute_config_hash(config)
    (previews_dir / f"{config_hash}.png").write_text("png")

    with pytest.raises(RuntimeError, match="Failed to create world"):
        create_world(config, config_hash)


def test_generate_preview_handles_permission_error(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        os.chmod(cwd, stat.S_IRUSR)
        raise PermissionError("Permission denied")

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(PermissionError):
        generate_preview(config)


def test_generate_preview_handles_missing_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "missing")

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError, match="Factorio binary not found"):
        generate_preview(config)


def test_generate_preview_cleans_tempdir_on_success(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    original_mkdtemp = tempfile.mkdtemp
    created_dirs = []

    def tracking_mkdtemp(*args, **kwargs):
        result = original_mkdtemp(*args, **kwargs)
        created_dirs.append(Path(result))
        return result

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)

    def mock_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    generate_preview(config)

    assert len(created_dirs) == 1
    assert not created_dirs[0].exists()


def test_generate_preview_cleans_tempdir_on_failure(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    original_mkdtemp = tempfile.mkdtemp
    created_dirs = []

    def tracking_mkdtemp(*args, **kwargs):
        result = original_mkdtemp(*args, **kwargs)
        created_dirs.append(Path(result))
        return result

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="Some Factorio error",
        )

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError, match="Failed to generate preview"):
        generate_preview(config)

    assert len(created_dirs) == 1
    assert not created_dirs[0].exists()


def test_create_world_cleans_tempdir_on_success(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    original_mkdtemp = tempfile.mkdtemp
    created_dirs = []

    def tracking_mkdtemp(*args, **kwargs):
        result = original_mkdtemp(*args, **kwargs)
        created_dirs.append(Path(result))
        return result

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)

    def mock_run(cmd, **kwargs):
        for arg in cmd:
            if arg.startswith("--create="):
                target = Path(arg.split("=", 1)[1])
                target.write_text("zip")
                break
        cwd = Path(kwargs.get("cwd", "."))
        (cwd / "preview.png").write_text("png")
        return None

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="NewWorld", planet="nauvis")
    preview = generate_preview(config)
    create_world(config, preview["preview_hash"])

    assert len(created_dirs) >= 1
    for d in created_dirs:
        assert not d.exists()


def test_create_world_cleans_tempdir_on_failure(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    original_mkdtemp = tempfile.mkdtemp
    created_dirs = []

    def tracking_mkdtemp(*args, **kwargs):
        result = original_mkdtemp(*args, **kwargs)
        created_dirs.append(Path(result))
        return result

    monkeypatch.setattr(tempfile, "mkdtemp", tracking_mkdtemp)

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="Some Factorio error",
        )

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    config_hash = _compute_config_hash(config)
    (previews_dir / f"{config_hash}.png").write_text("png")

    with pytest.raises(RuntimeError, match="Failed to create world"):
        create_world(config, config_hash)

    assert len(created_dirs) == 1
    assert not created_dirs[0].exists()


def test_cleanup_tempdir_removes_directory(tmp_path):
    target = tmp_path / "to-remove"
    target.mkdir()
    (target / "file.txt").write_text("x")
    assert target.exists()

    _cleanup_tempdir(target)

    assert not target.exists()


def test_cleanup_tempdir_handles_missing_directory(tmp_path):
    target = tmp_path / "does-not-exist"
    _cleanup_tempdir(target)


def test_cleanup_tempdir_handles_permission_error(tmp_path, monkeypatch):
    target = tmp_path / "readonly"
    target.mkdir()
    (target / "file.txt").write_text("x")
    target.chmod(stat.S_IRUSR)

    def mock_rmtree(path, *args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

    _cleanup_tempdir(target)


def test_generate_preview_handles_timeout(tmp_path, monkeypatch):
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 300)

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    with pytest.raises(RuntimeError, match="timed out"):
        generate_preview(config)


def test_create_world_handles_timeout(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "SAVE_DIR", saves_dir)
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(world_builder_service, "PREVIEWS_DIR", previews_dir)
    monkeypatch.setattr(world_builder_service, "INSTALL_DIR", tmp_path / "factorio")

    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    _write_fake_elf(factorio_bin)

    fake_module_file = tmp_path / "backend" / "services" / "world_builder_service.py"
    fake_module_file.parent.mkdir(parents=True, exist_ok=True)
    fake_module_file.write_text("")
    monkeypatch.setattr(world_builder_service, "__file__", str(fake_module_file))

    def mock_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 300)

    monkeypatch.setattr(world_builder_service.subprocess, "run", mock_run)

    config = DummyWorldConfig(world_name="TestWorld", planet="nauvis")
    config_hash = _compute_config_hash(config)
    (previews_dir / f"{config_hash}.png").write_text("png")

    with pytest.raises(RuntimeError, match="timed out"):
        create_world(config, config_hash)


def test_write_map_gen_settings_creates_file(tmp_path):
    config = DummyWorldConfig(
        world_name="Test",
        seed="123",
        random_seed=False,
        planet="nauvis",
        settings={"water": 0.5},
    )
    result = _write_map_gen_settings(config, tmp_path)

    assert result is not None
    assert result.exists()
    data = json.loads(result.read_text(encoding="utf-8"))
    assert data["seed"] == 123
    assert data["water"] == 0.5


def test_write_map_gen_settings_returns_none_when_empty(tmp_path):
    config = DummyWorldConfig(world_name="Test")
    result = _write_map_gen_settings(config, tmp_path)
    assert result is None


def test_write_map_settings_creates_file(tmp_path):
    config = DummyWorldConfig(
        world_name="Test",
        map_settings={"difficulty_settings": {"recipe_difficulty": 2}},
    )
    result = _write_map_settings(config, tmp_path)

    assert result is not None
    assert result.exists()
    data = json.loads(result.read_text(encoding="utf-8"))
    assert data["difficulty_settings"]["recipe_difficulty"] == 2


def test_write_map_settings_returns_none_when_empty(tmp_path):
    config = DummyWorldConfig(world_name="Test")
    result = _write_map_settings(config, tmp_path)
    assert result is None


def test_run_factorio_captures_execution_details(tmp_path):
    factorio_bin = tmp_path / "factorio" / "bin" / "x64" / "factorio"
    factorio_bin.parent.mkdir(parents=True, exist_ok=True)
    factorio_bin.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    factorio_bin.chmod(0o755)

    exec_info = _run_factorio([str(factorio_bin)], tmp_path)

    assert exec_info["return_code"] == 0
    assert "ok" in exec_info["stdout"]
    assert exec_info["elapsed_seconds"] >= 0
    assert len(exec_info["command"]) == 1


def test_move_generated_file_same_filesystem(tmp_path):
    src = tmp_path / "src" / "file.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("content")
    dst = tmp_path / "dst" / "file.txt"

    _move_generated_file(src, dst)

    assert not src.exists()
    assert dst.exists()
    assert dst.read_text() == "content"


def test_move_generated_file_cross_filesystem(tmp_path, monkeypatch):
    src = tmp_path / "src" / "file.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("content")
    dst = tmp_path / "dst" / "file.txt"

    def mock_move(s, d):
        raise OSError(18, "Invalid cross-device link")

    monkeypatch.setattr(shutil, "move", mock_move)

    with pytest.raises(OSError, match="Invalid cross-device link"):
        _move_generated_file(src, dst)


def test_move_generated_file_creates_destination_dir(tmp_path):
    src = tmp_path / "src" / "file.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("content")
    dst = tmp_path / "deep" / "nested" / "dir" / "file.txt"

    _move_generated_file(src, dst)

    assert not src.exists()
    assert dst.exists()


def test_move_generated_file_missing_source(tmp_path):
    src = tmp_path / "src" / "missing.txt"
    dst = tmp_path / "dst" / "file.txt"

    with pytest.raises(FileNotFoundError):
        _move_generated_file(src, dst)


def test_move_generated_file_failure_during_move(tmp_path, monkeypatch):
    src = tmp_path / "src" / "file.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("content")
    dst = tmp_path / "dst" / "file.txt"

    def mock_move(s, d):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(shutil, "move", mock_move)

    with pytest.raises(PermissionError, match="Permission denied"):
        _move_generated_file(src, dst)
