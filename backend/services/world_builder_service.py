from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.config import BASE_DIR, INSTALL_DIR, SAVE_DIR
from backend.services.world_config import WorldConfig

logger = logging.getLogger("fsm.world_builder")

WORLD_BUILDER_DIR = BASE_DIR / "data" / "world-builder"
PREVIEWS_DIR = WORLD_BUILDER_DIR / "previews"
MANIFEST_PATH = WORLD_BUILDER_DIR / "manifest.json"

DEFAULT_PLANETS = ["nauvis", "vulcanus", "fulgora", "gleba", "aquilo"]


def _get_factorio_bin() -> Optional[Path]:
    factorio_bin = INSTALL_DIR / "bin" / "x64" / "factorio"
    if not factorio_bin.exists():
        return None
    return factorio_bin


def validate_factorio_binary() -> dict[str, Any]:
    factorio_bin = _get_factorio_bin()
    if factorio_bin is None:
        return {
            "valid": False,
            "reason": "not_installed",
            "message": "World Builder preview unavailable. Factorio installation is not complete.",
        }

    try:
        with open(factorio_bin, "rb") as f:
            magic = f.read(4)
    except OSError as exc:
        raise RuntimeError(f"Factorio binary not readable: {exc}") from exc

    if magic != b"\x7fELF":
        return {
            "valid": False,
            "reason": "placeholder",
            "message": "World Builder Preview indisponível. Instalação do Factorio não concluída.",
        }

    return {"valid": True, "reason": "ok"}


def _ensure_dirs() -> None:
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)


def _compute_config_hash(config: WorldConfig) -> str:
    payload = json.dumps(
        {
            "world_name": config.world_name,
            "seed": config.seed,
            "random_seed": config.random_seed,
            "planet": config.planet,
            "settings": config.settings,
            "map_settings": config.map_settings,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_map_gen_settings(config: WorldConfig, directory: Path) -> Optional[Path]:
    if not config.settings:
        return None

    settings = {
        "seed": int(config.seed) if (config.seed and not config.random_seed) else None,
        "planet": config.planet,
        **config.settings,
    }
    settings = {k: v for k, v in settings.items() if v is not None}

    path = directory / "map-gen-settings.json"
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return path


def _write_map_settings(config: WorldConfig, directory: Path) -> Optional[Path]:
    if not config.map_settings:
        return None

    path = directory / "map-settings.json"
    path.write_text(json.dumps(config.map_settings, indent=2), encoding="utf-8")
    return path


def list_planets() -> list[str]:
    return list(DEFAULT_PLANETS)


def _run_factorio(cmd: list[str], tmpdir: Path) -> dict[str, Any]:
    start = time.time()
    result = subprocess.run(
        cmd,
        cwd=str(tmpdir),
        capture_output=True,
        text=True,
        timeout=300,
    )
    elapsed = time.time() - start
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return_code = getattr(result, "returncode", 0)
    return {
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": return_code,
        "elapsed_seconds": round(elapsed, 3),
    }


def _cleanup_tempdir(tmpdir: Path) -> None:
    try:
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
    except OSError as exc:
        logger.warning("Failed to cleanup temp directory %s: %s", tmpdir, exc)


def _move_generated_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    if not destination.exists():
        raise RuntimeError(f"File move failed: {source} -> {destination}")


def generate_preview(config: WorldConfig) -> dict[str, Any]:
    _ensure_dirs()

    validation = validate_factorio_binary()
    if not validation.get("valid"):
        raise RuntimeError(validation.get("message", "Invalid Factorio installation."))

    factorio_bin = _get_factorio_bin()
    config_hash = _compute_config_hash(config)
    preview_path = PREVIEWS_DIR / f"{config_hash}.png"

    if preview_path.exists():
        return {
            "preview_url": f"/api/world-builder/preview-image/{config_hash}.png",
            "preview_hash": config_hash,
            "status": "ready",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    tmpdir = Path(tempfile.mkdtemp(prefix="world-builder-"))
    map_gen_settings_path = None
    map_settings_path = None

    def _list_directory(path: Path) -> list[str]:
        if not path.exists():
            return ["<diretório não existe>"]
        return sorted(p.name for p in path.iterdir())

    def _png_files(path: Path) -> list[str]:
        return sorted(p.name for p in path.glob("*.png")) if path.exists() else []

    try:
        map_gen_settings_path = _write_map_gen_settings(config, tmpdir)
        map_settings_path = _write_map_settings(config, tmpdir)

        cmd = [str(factorio_bin), "--generate-map-preview", "preview.png"]
        if map_gen_settings_path:
            cmd.append(f"--map-gen-settings={map_gen_settings_path.name}")
        if map_settings_path:
            cmd.append(f"--map-settings={map_settings_path.name}")
        if config.seed and not config.random_seed:
            cmd.append(f"--map-gen-seed={config.seed}")
        cmd.extend(["--map-preview-size", "1024"])
        if config.planet:
            cmd.append(f"--map-preview-planet={config.planet}")

        exec_info = _run_factorio(cmd, tmpdir)
        logger.info(
            "Preview generation completed. Command: %s | Return code: %s | Time: %ss",
            " ".join(exec_info["command"]),
            exec_info["return_code"],
            exec_info["elapsed_seconds"],
        )
        if exec_info["stdout"]:
            logger.debug("Preview stdout: %s", exec_info["stdout"])
        if exec_info["stderr"]:
            logger.debug("Preview stderr: %s", exec_info["stderr"])

        generated = tmpdir / "preview.png"
        if not generated.exists():
            files = _list_directory(tmpdir)
            pngs = _png_files(tmpdir)
            details = (
                f"Comando: {' '.join(exec_info['command'])}\n"
                f"cwd: {tmpdir}\n"
                f"stdout: {exec_info['stdout']}\n"
                f"stderr: {exec_info['stderr']}\n"
                f"return code: {exec_info['return_code']}\n"
                f"tempo: {exec_info['elapsed_seconds']}s\n"
                f"preview.png existe: False\n"
                f"PNGs encontrados: {pngs if pngs else 'nenhum'}\n"
                f"arquivos no diretório temporário:\n"
                + "\n".join(f"  {f}" for f in files)
            )
            logger.error("Preview generation failed. Details:\n%s", details)
            raise RuntimeError(
                "Factorio executou com sucesso mas não gerou preview.png.\n" + details
            )

        _move_generated_file(generated, preview_path)

        logger.info(
            "DIAGNOSTIC preview generated: path=%s exists=%s size=%s hash=%s",
            preview_path,
            preview_path.exists(),
            preview_path.stat().st_size if preview_path.exists() else None,
            config_hash,
        )
    except subprocess.CalledProcessError as exc:
        files = _list_directory(tmpdir)
        pngs = _png_files(tmpdir)
        logger.error(
            "Failed to generate preview. Command: %s | Return code: %s | Stderr: %s | Files: %s | PNGs: %s",
            " ".join(exc.cmd) if exc.cmd else "unknown",
            exc.returncode,
            exc.stderr,
            files,
            pngs,
        )
        raise RuntimeError(
            "Failed to generate preview.\n"
            f"Comando: {' '.join(exc.cmd) if exc.cmd else 'unknown'}\n"
            f"cwd: {tmpdir}\n"
            f"stdout: {getattr(exc, 'stdout', '')}\n"
            f"stderr: {exc.stderr}\n"
            f"return code: {exc.returncode}\n"
            f"arquivos no diretório temporário:\n"
            + "\n".join(f"  {f}" for f in files)
        ) from exc
    except subprocess.TimeoutExpired:
        files = _list_directory(tmpdir)
        pngs = _png_files(tmpdir)
        logger.error(
            "Preview generation timed out after 300s. Files: %s | PNGs: %s",
            files,
            pngs,
        )
        raise RuntimeError(
            "Preview generation timed out.\n"
            f"cwd: {tmpdir}\n"
            f"arquivos no diretório temporário:\n"
            + "\n".join(f"  {f}" for f in files)
        )
    except Exception as exc:
        logger.error("Unexpected error during preview generation: %s", exc, exc_info=True)
        raise
    finally:
        _cleanup_tempdir(tmpdir)

    _append_manifest(config, config_hash, preview_path)

    return {
        "preview_url": f"/api/world-builder/preview-image/{config_hash}.png",
        "preview_hash": config_hash,
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_world(config: WorldConfig, preview_hash: str) -> dict[str, Any]:
    validation = validate_factorio_binary()
    if not validation.get("valid"):
        raise RuntimeError(validation.get("message", "Invalid Factorio installation."))

    factorio_bin = _get_factorio_bin()
    config_hash = _compute_config_hash(config)

    if preview_hash != config_hash:
        raise ValueError("Preview hash does not match current configuration. Update preview first.")

    if not config.world_name.endswith(".zip"):
        save_name = f"{config.world_name}.zip"
    else:
        save_name = config.world_name

    target = SAVE_DIR / save_name
    if target.exists():
        raise FileExistsError(f"Save already exists: {save_name}")

    tmpdir = Path(tempfile.mkdtemp(prefix="world-builder-"))
    map_gen_settings_path = None
    map_settings_path = None
    temp_save = tmpdir / save_name

    try:
        map_gen_settings_path = _write_map_gen_settings(config, tmpdir)
        map_settings_path = _write_map_settings(config, tmpdir)

        cmd = [str(factorio_bin), f"--create={temp_save}"]
        if map_gen_settings_path:
            cmd.append(f"--map-gen-settings={map_gen_settings_path.name}")
        if map_settings_path:
            cmd.append(f"--map-settings={map_settings_path.name}")
        if config.seed and not config.random_seed:
            cmd.append(f"--map-gen-seed={config.seed}")

        exec_info = _run_factorio(cmd, tmpdir)
        logger.info(
            "World creation completed. Command: %s | Return code: %s | Time: %ss",
            " ".join(exec_info["command"]),
            exec_info["return_code"],
            exec_info["elapsed_seconds"],
        )
        if exec_info["stdout"]:
            logger.debug("World creation stdout: %s", exec_info["stdout"])
        if exec_info["stderr"]:
            logger.debug("World creation stderr: %s", exec_info["stderr"])

        if not temp_save.exists():
            raise RuntimeError("Factorio did not create the save file")

        _move_generated_file(temp_save, target)
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Failed to create world. Command: %s | Return code: %s | Stderr: %s",
            " ".join(exc.cmd) if exc.cmd else "unknown",
            exc.returncode,
            exc.stderr,
        )
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        raise RuntimeError("Failed to create world. Check server logs for details.") from exc
    except subprocess.TimeoutExpired:
        logger.error("World creation timed out after 300s")
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        raise RuntimeError("World creation timed out.")
    except Exception as exc:
        logger.error("Unexpected error during world creation: %s", exc, exc_info=True)
        raise
    finally:
        _cleanup_tempdir(tmpdir)

    logger.info("Created new world save: %s", save_name)
    return {
        "save_file": save_name,
        "save_path": str(target),
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _append_manifest(config: WorldConfig, config_hash: str, preview_path: Path) -> None:
    manifest = {"previews": []}
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {"previews": []}

    manifest.setdefault("previews", [])
    manifest["previews"].append(
        {
            "hash": config_hash,
            "world_name": config.world_name,
            "seed": config.seed,
            "random_seed": config.random_seed,
            "planet": config.planet,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_path": str(preview_path),
        }
    )

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
