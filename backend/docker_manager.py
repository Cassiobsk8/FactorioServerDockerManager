import json
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
from typing import Dict, List, Optional, Union

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "backend" / "server_config.json"
SAVE_DIR = BASE_DIR / "data" / "saves"
INSTALL_DIR = BASE_DIR / "factorio"
LOG_DIR = BASE_DIR / "logs"
PID_PATH = BASE_DIR / "backend" / "server.pid"
INSTALL_PROGRESS_PATH = LOG_DIR / "install_progress.json"

DEFAULT_CONFIG: Dict[str, str] = {
    "server_name": "factorio",
    "server_password": "change-me",
}

DEFAULT_INSTALL_ARCHIVE = os.getenv("FACTORIO_SERVER_ARCHIVE", "")
DEFAULT_INSTALL_URL = os.getenv(
    "FACTORIO_SERVER_ARCHIVE_URL",
    "https://factorio.com/get-download/stable/headless/linux64",
)


class ServerManager:
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
        process = subprocess.Popen(
            cmd,
            cwd=str(INSTALL_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        _write_pid(process.pid)
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
        _extract_archive(archive)
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
    elif archive_type == "tar.xz" or archive_type == "tar.gz" or archive_type == "tar.bz2":
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


def _get_log_file() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / "factorio-console.log"


def _get_factorio_generated_log_file() -> Path:
    console_log = _get_log_file()
    if console_log.exists():
        return console_log

    for candidate in [INSTALL_DIR / "factorio-current.log", INSTALL_DIR / "factorio-previous.log"]:
        if candidate.exists():
            return candidate

    return console_log


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


def get_logs() -> str:
    log_file = _get_factorio_generated_log_file()
    if not log_file.exists():
        return ""
    return log_file.read_text(encoding="utf-8")


def clear_logs() -> None:
    log_file = _get_factorio_generated_log_file()
    if log_file.exists():
        log_file.write_text("", encoding="utf-8")


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


def load_server_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, str]:
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


def get_save_directory() -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return SAVE_DIR


def list_save_files() -> List[str]:
    return sorted(path.name for path in get_save_directory().glob("*") if path.is_file())


def save_uploaded_file(uploaded_file) -> str:
    if uploaded_file.filename == "":
        raise ValueError("Empty file name")

    destination = get_save_directory() / uploaded_file.filename
    uploaded_file.save(destination)
    return destination.name


def log_error(message: str) -> None:
    log_file = _get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handler:
        handler.write(message + "\n")


def _factorio_command() -> List[str]:
    factorio_bin = INSTALL_DIR / "bin" / "x64" / "factorio"
    if not factorio_bin.exists():
        raise RuntimeError("Factorio binary not found. Install the server first.")

    save_dir = get_save_directory()
    auto_save = save_dir / "autosave.zip"
    console_log = _get_log_file()
    cmd = [str(factorio_bin), "--console-log", str(console_log)]

    if auto_save.exists():
        cmd.append(f"--start-server={auto_save}")
    else:
        cmd.extend([f"--create={auto_save}", f"--start-server={auto_save}"])

    return cmd