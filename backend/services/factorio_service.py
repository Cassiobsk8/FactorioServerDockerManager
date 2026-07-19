from __future__ import annotations

import json
import logging
import os
import platform
import re
import signal
import shutil
import subprocess
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backend.config import (
    BASE_DIR,
    CONFIG_PATH,
    DEFAULT_INSTALL_ARCHIVE,
    DEFAULT_INSTALL_URL,
    INSTALL_DIR,
    INSTALL_LOG_PATH,
    INSTALL_PROGRESS_PATH,
    LOG_DIR,
    PID_PATH,
    SAVE_DIR,
    SERVER_LOG_PATH,
    SERVER_SETTINGS_DIR,
    SERVER_SETTINGS_EXAMPLE_PATH,
    SERVER_SETTINGS_PATH,
    ADMINLIST_PATH,
    BANLIST_PATH,
    WHITELIST_PATH,
)
from backend.services.save_service import load_active_save
from backend.services.settings_service import load_app_settings
from backend.services.startup_builder import RuntimeStartupBuilder, StartupConfiguration

logger = logging.getLogger("fsm.factorio")


class FactorioService:
    """Encapsulates all Factorio server lifecycle operations."""

    def get_status(self) -> str:
        if not is_server_installed():
            return "not_installed"
        pid = _read_pid()
        if pid is None or not _is_process_running(pid):
            return "stopped"
        return "running"

    def start_server(self) -> str:
        if not is_server_installed():
            raise RuntimeError("Server is not installed")

        if not is_platform_supported():
            raise RuntimeError(
                "Factorio server startup is supported only on Linux hosts/containers. "
                "The downloaded headless archive is Linux-only and cannot execute on Windows."
            )

        pid = _read_pid()
        if pid is not None and _is_process_running(pid):
            return "already running"

        cmd = _factorio_command()
        logger.info("Starting factorio server with cmd: %s", cmd)
        log_file = _get_server_log_file()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_file.open("ab")

        process = subprocess.Popen(
            cmd,
            cwd=str(INSTALL_DIR),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        log_handle.close()
        _write_pid(process.pid)
        logger.info("Factorio started (pid=%s)", process.pid)
        return "started"

    def stop_server(self) -> str:
        pid = _read_pid()
        if pid is None:
            return "not running"

        if _is_process_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

            for _ in range(20):
                if not _is_process_running(pid):
                    break
                time.sleep(0.1)

        _clear_pid()
        logger.info("Factorio stopped (pid=%s)", pid)
        return "stopped"

    def restart_server(self) -> str:
        self.stop_server()
        return self.start_server()

    def install_server(self, archive_path: Optional[str] = None) -> str:
        if is_server_installed():
            return "already installed"

        if archive_path:
            if archive_path.startswith("http://") or archive_path.startswith("https://"):
                archive = _download_archive(archive_path)
            else:
                source = Path(archive_path)
                if not source.exists():
                    raise FileNotFoundError(f"Archive not found: {archive_path}")
                archive = source
        elif DEFAULT_INSTALL_ARCHIVE:
            archive = Path(DEFAULT_INSTALL_ARCHIVE)
            if not archive.exists():
                raise FileNotFoundError(f"Archive not found: {archive}")
        elif DEFAULT_INSTALL_URL:
            archive = _download_archive(DEFAULT_INSTALL_URL)
        else:
            raise RuntimeError(
                "No Factorio server archive configured. Set FACTORIO_SERVER_ARCHIVE or FACTORIO_SERVER_ARCHIVE_URL."
            )

        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Installing server from archive: %s", archive)
        try:
            _extract_archive(archive)
        except Exception:
            logger.exception("Extraction failed")
            raise
        logger.info("Installation completed")
        return "installed"

    def get_install_status(self) -> str:
        if is_server_installed():
            return "installed"
        if DEFAULT_INSTALL_ARCHIVE:
            return f"configured archive: {Path(DEFAULT_INSTALL_ARCHIVE).name}"
        if DEFAULT_INSTALL_URL:
            return "configured install URL"
        return "not installed"


def _read_pid() -> Optional[int]:
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _write_pid(pid: int) -> None:
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(pid), encoding="utf-8")


def _clear_pid() -> None:
    if PID_PATH.exists():
        PID_PATH.unlink()


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def is_platform_supported() -> bool:
    return platform.system() == "Linux"


def _download_archive(url: str) -> Path:
    parsed = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name or "factorio_headless"
    target = BASE_DIR / filename
    if target.exists():
        target.unlink()

    target.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    with urllib.request.urlopen(request) as response:
        content_length = response.getheader("Content-Length")
        total = int(content_length) if content_length and content_length.isdigit() else 0
        _set_install_progress(
            status="progress",
            stage="download",
            message="Downloading server archive...",
            downloaded=0,
            total=total,
        )

        content_disposition = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disposition:
            filename_match = re.search(r'filename="?([^";]+)"?', content_disposition)
            if filename_match:
                target = BASE_DIR / filename_match.group(1)
        else:
            final_url = response.geturl()
            final_name = Path(urllib.parse.urlparse(final_url).path).name
            if final_name:
                target = BASE_DIR / final_name

        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out_file:
            downloaded = 0
            chunk_size = 8192
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                _set_install_progress(
                    status="progress",
                    stage="download",
                    message="Downloading server archive...",
                    downloaded=downloaded,
                    total=total,
                )

    logger.info("Downloaded archive to %s", target)
    return target


def _extract_archive(archive_path: Path) -> None:
    archive_type = None
    if archive_path.suffix == ".zip":
        archive_type = "zip"
    elif archive_path.suffixes[-2:] == [".tar", ".xz"] or archive_path.suffix == ".xz":
        archive_type = "tar.xz"
    else:
        with archive_path.open("rb") as file:
            header = file.read(8)
            if header.startswith(b"PK"):
                archive_type = "zip"
            elif header.startswith(b"\x1f\x8b") or header.startswith(b"7z"):
                archive_type = "tar.xz"

    if archive_type == "zip":
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(INSTALL_DIR)
    elif archive_type in ("tar.xz", "tar.gz", "tar.bz2"):
        with tarfile.open(archive_path, "r:*") as archive:
            archive.extractall(INSTALL_DIR)
    else:
        raise RuntimeError("Unsupported archive format. Use .zip, .tar.xz, .tar.gz or .tar.bz2")

    _set_install_progress(
        status="progress",
        stage="install",
        message="Extracting and installing server...",
        downloaded=0,
        total=0,
    )
    _normalize_install_directory()
    _set_install_progress(
        status="complete",
        stage="done",
        message="Installation completed successfully.",
        downloaded=0,
        total=0,
    )


def _normalize_install_directory() -> None:
    expected_bin = INSTALL_DIR / "bin" / "x64" / "factorio"
    if expected_bin.exists():
        return

    nested_bin = next(
        (path for path in INSTALL_DIR.rglob("bin/x64/factorio") if path.is_file()),
        None,
    )
    if nested_bin is None:
        extracted_items = [str(path.relative_to(INSTALL_DIR)) for path in INSTALL_DIR.iterdir()]
        raise RuntimeError(
            f"Archive extracted but Factorio binary not found in expected location. "
            f"Extracted entries: {extracted_items}"
        )

    nested_root = nested_bin
    while nested_root.parent != INSTALL_DIR:
        nested_root = nested_root.parent

    if nested_root == INSTALL_DIR:
        raise RuntimeError("Unexpected install layout after extraction")

    for child in nested_root.iterdir():
        target = INSTALL_DIR / child.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(child), str(target))

    if nested_root.exists():
        shutil.rmtree(nested_root)

    if not expected_bin.exists():
        raise RuntimeError("Factorio binary not found after normalizing extracted archive layout")


def is_server_installed() -> bool:
    return (INSTALL_DIR / "bin" / "x64" / "factorio").exists()


def _get_server_log_file() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return SERVER_LOG_PATH


def _get_install_log_file() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return INSTALL_LOG_PATH


def _get_factorio_generated_log_file() -> Path:
    log_file = _get_server_log_file()
    if log_file.exists():
        return log_file

    for candidate in [
        INSTALL_DIR / "factorio-current.log",
        INSTALL_DIR / "factorio-previous.log",
        INSTALL_DIR / "logs" / "factorio-current.log",
    ]:
        if candidate.exists():
            return candidate

    return log_file


def _get_install_progress_file() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return INSTALL_PROGRESS_PATH


def _write_install_progress(progress: Dict[str, Union[str, int]]):
    progress_file = _get_install_progress_file()
    progress_file.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def _read_install_progress() -> Dict[str, Union[str, int]]:
    progress_file = _get_install_progress_file()
    if not progress_file.exists():
        return {"status": "idle", "stage": "none", "downloaded": 0, "total": 0, "message": "Idle."}

    try:
        return json.loads(progress_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "idle", "stage": "none", "downloaded": 0, "total": 0, "message": "Idle."}


def _clear_install_progress() -> None:
    progress_file = _get_install_progress_file()
    if progress_file.exists():
        progress_file.unlink()


def clear_install_progress() -> None:
    _clear_install_progress()


def _set_install_progress(
    status: str,
    stage: str,
    message: str,
    downloaded: int = 0,
    total: int = 0,
):
    _write_install_progress(
        {
            "status": status,
            "stage": stage,
            "message": message,
            "downloaded": downloaded,
            "total": total,
        }
    )


def get_install_progress() -> Dict[str, Union[str, int]]:
    return _read_install_progress()


def set_install_error(message: str) -> None:
    _set_install_progress(
        status="error",
        stage="failed",
        message=message,
        downloaded=0,
        total=0,
    )


def _install_in_progress() -> bool:
    progress = _read_install_progress()
    return progress.get("status") == "progress"


def get_logs() -> str:
    if not is_server_installed():
        return "Servidor não instalado."

    if _install_in_progress():
        log_file = _get_install_log_file()
    else:
        log_file = _get_server_log_file()

    if log_file.exists():
        return log_file.read_text(encoding="utf-8", errors="replace")

    log_file = _get_factorio_generated_log_file()
    if log_file.exists():
        return log_file.read_text(encoding="utf-8", errors="replace")

    return ""


def clear_logs() -> None:
    if _install_in_progress():
        log_file = _get_install_log_file()
    else:
        log_file = _get_server_log_file()

    if log_file.exists():
        log_file.write_text("", encoding="utf-8")

    generated_log_file = _get_factorio_generated_log_file()
    if generated_log_file.exists() and generated_log_file != log_file:
        generated_log_file.write_text("", encoding="utf-8")


def clear_install_logs() -> None:
    log_file = _get_install_log_file()
    if log_file.exists():
        log_file.write_text("", encoding="utf-8")


def begin_install_logging() -> logging.Handler:
    log_file = _get_install_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(handler)
    return handler


def end_install_logging(handler: logging.Handler) -> None:
    logging.getLogger().removeHandler(handler)
    handler.close()


def clear_installation() -> None:
    pid = _read_pid()
    if pid is not None and _is_process_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

        for _ in range(20):
            if not _is_process_running(pid):
                break
            time.sleep(0.1)

    _clear_pid()

    if INSTALL_DIR.exists():
        try:
            shutil.rmtree(INSTALL_DIR)
        except OSError as exc:
            log_error(f"Clear installation failed while removing install directory: {exc}")

    if LOG_DIR.exists():
        try:
            shutil.rmtree(LOG_DIR)
        except OSError as exc:
            log_error(f"Clear installation failed while removing log directory: {exc}")

    clear_logs()
    clear_install_progress()


def load_server_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, str]:
    from backend.config import DEFAULT_CONFIG

    path = Path(config_path or CONFIG_PATH)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}

    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if isinstance(v, str)})
    return merged


def save_server_config(
    config_path: Optional[Union[str, Path]] = None,
    values: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    path = Path(config_path or CONFIG_PATH)
    current = load_server_config(path)

    if values:
        current.update({k: v for k, v in values.items() if isinstance(v, str)})

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def load_server_settings(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    path = Path(config_path or SERVER_SETTINGS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        if SERVER_SETTINGS_EXAMPLE_PATH.exists():
            shutil.copy(SERVER_SETTINGS_EXAMPLE_PATH, path)
            logger.info("Copied example server-settings to %s", path)
        else:
            path.write_text(json.dumps({}, indent=2), encoding="utf-8")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        raw = ""

    if not raw or raw.strip() == "":
        if SERVER_SETTINGS_EXAMPLE_PATH.exists():
            shutil.copy(SERVER_SETTINGS_EXAMPLE_PATH, path)
            logger.info("Replaced empty server-settings with example at %s", path)
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        else:
            return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        if SERVER_SETTINGS_EXAMPLE_PATH.exists():
            shutil.copy(SERVER_SETTINGS_EXAMPLE_PATH, path)
            logger.warning("Invalid server-settings JSON; replaced with example at %s", path)
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    if isinstance(parsed, dict):
        keys = list(parsed.keys())
        only_comments = bool(keys) and all(isinstance(k, str) and k.startswith("_comment_") for k in keys)
        if not keys or only_comments:
            if SERVER_SETTINGS_EXAMPLE_PATH.exists():
                shutil.copy(SERVER_SETTINGS_EXAMPLE_PATH, path)
                logger.info("Server-settings was empty or comments-only; replaced with example at %s", path)
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    return {}
            return {}

    return parsed


def save_server_settings(settings: Dict[str, Any], config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    path = Path(config_path or SERVER_SETTINGS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    logger.info("Saved server-settings to %s", path)
    return settings


def build_server_settings_fields(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    def _recursive_build(data: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
        comments = {
            key[len("_comment_"):]: value
            for key, value in data.items()
            if isinstance(key, str) and key.startswith("_comment_")
        }

        fields: List[Dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(key, str) and key.startswith("_comment_"):
                continue

            path = f"{prefix}.{key}" if prefix else key
            comment = comments.get(key)

            if isinstance(value, dict):
                fields.append(
                    {
                        "key": key,
                        "path": path,
                        "comment": comment,
                        "type": "object",
                        "children": _recursive_build(value, path),
                    }
                )
            elif isinstance(value, bool):
                fields.append({"key": key, "path": path, "comment": comment, "type": "boolean", "value": value})
            elif isinstance(value, int):
                fields.append({"key": key, "path": path, "comment": comment, "type": "integer", "value": value})
            elif isinstance(value, float):
                fields.append({"key": key, "path": path, "comment": comment, "type": "number", "value": value})
            elif isinstance(value, list):
                fields.append(
                    {
                        "key": key,
                        "path": path,
                        "comment": comment,
                        "type": "json",
                        "value": json.dumps(value, indent=2, ensure_ascii=False),
                    }
                )
            else:
                fields.append({"key": key, "path": path, "comment": comment, "type": "string", "value": value})

        return fields

    return _recursive_build(settings)


def _get_nested_value(data: Any, path_parts: List[str]) -> Any:
    current = data
    for part in path_parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_nested_value(data: Dict[str, Any], path_parts: List[str], value: Any) -> None:
    current: Dict[str, Any] = data
    for part in path_parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[path_parts[-1]] = value


def _parse_setting_value(raw_value: str, existing_value: Any) -> Any:
    if isinstance(existing_value, bool):
        return raw_value.lower() == "true"

    if isinstance(existing_value, int) and not isinstance(existing_value, bool):
        try:
            return int(raw_value)
        except ValueError:
            return existing_value

    if isinstance(existing_value, float):
        try:
            return float(raw_value)
        except ValueError:
            return existing_value

    if isinstance(existing_value, list) or isinstance(existing_value, dict):
        try:
            parsed = json.loads(raw_value)
            return parsed
        except json.JSONDecodeError:
            return existing_value

    return raw_value


def update_server_settings_from_form(form: Dict[str, str], current_settings: Dict[str, Any]) -> Dict[str, Any]:
    updated = json.loads(json.dumps(current_settings))

    for raw_key, raw_value in form.items():
        if not raw_key.startswith("settings."):
            continue

        path = raw_key[len("settings.") :]
        if not path:
            continue

        path_parts = path.split(".")
        existing_value = _get_nested_value(current_settings, path_parts)
        parsed_value = _parse_setting_value(raw_value, existing_value)
        _set_nested_value(updated, path_parts, parsed_value)

    return updated


def _factorio_command(install_dir: Optional[Path] = None) -> List[str]:
    base = install_dir if install_dir is not None else INSTALL_DIR
    factorio_bin = base / "bin" / "x64" / "factorio"
    if not factorio_bin.exists():
        raise RuntimeError("Factorio binary not found. Install the server first.")

    active_save = load_active_save()
    if active_save is None:
        raise RuntimeError(
            "No active save configured. Create a new world, upload a save, or select an existing save before starting the server."
        )

    app_settings = load_app_settings()
    rcon_host = app_settings.get("rcon_host", "127.0.0.1")
    rcon_port = app_settings.get("rcon_port", "27015")
    rcon_password = app_settings.get("rcon_password", "")
    server_port = app_settings.get("server_port", "")
    bind = app_settings.get("bind", "")
    rcon_bind = app_settings.get("rcon_bind", rcon_host)
    server_id_raw = app_settings.get("server_id", "")
    server_id = Path(server_id_raw) if server_id_raw else None
    use_authserver_bans = app_settings.get("use_authserver_bans", "false").lower() == "true"
    factorio_username = app_settings.get("factorio_username", "")
    factorio_token = app_settings.get("factorio_service_token", "")

    logger.info("RCON Host: %s", rcon_host)
    logger.info("RCON Port: %s", rcon_port)
    logger.info("RCON Enabled: %s", bool(rcon_password))

    config = StartupConfiguration(
        factorio_bin=factorio_bin,
        active_save=active_save,
        rcon_port=rcon_port,
        rcon_password=rcon_password,
        port=server_port or None,
        bind=bind or None,
        rcon_bind=rcon_bind or None,
        server_id=server_id,
        use_authserver_bans=use_authserver_bans,
        server_settings=SERVER_SETTINGS_PATH if SERVER_SETTINGS_PATH.exists() else None,
        adminlist=ADMINLIST_PATH if ADMINLIST_PATH.exists() else None,
        banlist=BANLIST_PATH if BANLIST_PATH.exists() else None,
        whitelist=WHITELIST_PATH if WHITELIST_PATH.exists() else None,
    )

    builder = RuntimeStartupBuilder(config)
    return builder.build()


def log_error(message: str) -> None:
    log_file = _get_server_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handler:
        handler.write(message + "\n")
