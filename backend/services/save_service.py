from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from backend.config import ACTIVE_SAVE_PATH, SAVE_DIR

logger = logging.getLogger("fsm.saves")


def get_save_directory(save_dir: Optional[Path] = None) -> Path:
    target = save_dir if save_dir is not None else SAVE_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def list_save_files(save_dir: Optional[Path] = None) -> list[str]:
    directory = get_save_directory(save_dir)
    return sorted(path.name for path in directory.glob("*.zip") if path.is_file())


def save_uploaded_file(uploaded_file, save_dir: Optional[Path] = None) -> str:
    if uploaded_file.filename == "":
        raise ValueError("Empty file name")

    destination = get_save_directory(save_dir) / uploaded_file.filename
    uploaded_file.save(destination)
    return destination.name


def get_active_save() -> Optional[str]:
    if not ACTIVE_SAVE_PATH.exists():
        return None
    try:
        data = json.loads(ACTIVE_SAVE_PATH.read_text(encoding="utf-8"))
        return data.get("active_save")
    except (json.JSONDecodeError, OSError):
        return None


def load_active_save() -> Optional[Path]:
    active = get_active_save()
    if active is None:
        return None
    target = get_save_directory() / active
    return target if target.exists() else None


def select_save(filename: str) -> dict:
    if not filename.endswith(".zip"):
        raise ValueError("Save file must be a .zip archive")

    target = get_save_directory() / filename
    if not target.exists():
        raise FileNotFoundError(f"Save not found: {filename}")

    ACTIVE_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_SAVE_PATH.write_text(
        json.dumps({"active_save": filename}, indent=2),
        encoding="utf-8",
    )
    logger.info("Selected active save: %s", filename)
    return {"active_save": filename}


def create_save(name: str, seed: Optional[str] = None) -> dict:
    if not name.endswith(".zip"):
        name = f"{name}.zip"

    target = get_save_directory() / name
    if target.exists():
        raise FileExistsError(f"Save already exists: {name}")

    factorio_bin = Path(__file__).resolve().parent.parent.parent / "factorio" / "bin" / "x64" / "factorio"
    if not factorio_bin.exists():
        raise RuntimeError("Factorio binary not found. Install the server first.")

    cmd = [str(factorio_bin), f"--create={target}"]
    if seed:
        cmd.extend([f"--map-gen-seed={seed}"])

    try:
        subprocess.run(
            cmd,
            cwd=str(factorio_bin.parent.parent.parent),
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Failed to create save: %s", exc.stderr)
        raise RuntimeError(f"Failed to create save: {exc.stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("Save creation timed out")
        raise RuntimeError("Save creation timed out") from exc

    select_save(name)
    logger.info("Created new save: %s", name)
    return {"name": name, "status": "created", "active": True}


def delete_save(filename: str) -> dict:
    if not filename.endswith(".zip"):
        filename = f"{filename}.zip"

    target = get_save_directory() / filename
    if not target.exists():
        raise FileNotFoundError(f"Save not found: {filename}")

    active = get_active_save()
    if active == filename:
        raise ValueError("Cannot delete the active save. Select another save first.")

    try:
        target.unlink()
        logger.info("Deleted save: %s", filename)
        return {"status": "deleted", "filename": filename}
    except OSError as exc:
        logger.error("Failed to delete save %s: %s", filename, exc)
        raise RuntimeError(f"Failed to delete save: {exc}") from exc


def rename_save(old_name: str, new_name: str) -> dict:
    if not old_name.endswith(".zip"):
        old_name = f"{old_name}.zip"
    if not new_name.endswith(".zip"):
        new_name = f"{new_name}.zip"

    source = get_save_directory() / old_name
    if not source.exists():
        raise FileNotFoundError(f"Save not found: {old_name}")

    destination = get_save_directory() / new_name
    if destination.exists():
        raise FileExistsError(f"Save already exists: {new_name}")

    active = get_active_save()
    if active == old_name:
        select_save(new_name)

    try:
        source.rename(destination)
        logger.info("Renamed save: %s -> %s", old_name, new_name)
        return {"status": "renamed", "old_name": old_name, "new_name": new_name}
    except OSError as exc:
        logger.error("Failed to rename save %s: %s", old_name, exc)
        raise RuntimeError(f"Failed to rename save: {exc}") from exc


def get_save_info(filename: str) -> dict:
    if not filename.endswith(".zip"):
        filename = f"{filename}.zip"

    path = get_save_directory() / filename
    if not path.exists():
        raise FileNotFoundError(f"Save not found: {filename}")

    stat = path.stat()
    active = get_active_save()
    return {
        "name": filename,
        "size": stat.st_size,
        "modified": int(stat.st_mtime),
        "active": active == filename,
    }
