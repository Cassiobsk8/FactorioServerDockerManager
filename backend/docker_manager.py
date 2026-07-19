from __future__ import annotations

import platform

from backend.config import (
    BASE_DIR,
    CONFIG_PATH,
    DEFAULT_CONFIG,
    DEFAULT_INSTALL_ARCHIVE,
    DEFAULT_INSTALL_URL,
    INSTALL_DIR,
    INSTALL_PROGRESS_PATH,
    LOG_DIR,
    PID_PATH,
    SAVE_DIR,
    SERVER_SETTINGS_DIR,
    SERVER_SETTINGS_EXAMPLE_PATH,
    SERVER_SETTINGS_PATH,
)
from backend.services.factorio_service import (
    _clear_pid,
    _extract_archive,
    _get_factorio_generated_log_file,
    _get_server_log_file,
    _is_process_running,
    _read_pid,
    _write_pid,
    _factorio_command as _factorio_command_impl,
    clear_installation,
    clear_install_progress,
    clear_logs,
    get_install_progress,
    get_logs,
    is_platform_supported,
    is_server_installed,
    load_server_config,
    load_server_settings,
    log_error,
    save_server_config,
    save_server_settings,
    set_install_error,
    update_server_settings_from_form,
    build_server_settings_fields,
)
from backend.services.startup_builder import RuntimeStartupBuilder
from backend.services.save_service import save_uploaded_file as _save_uploaded_file, get_save_directory as _get_save_directory, list_save_files as _list_save_files
from backend.services.factorio_service import FactorioService

ServerManager = FactorioService


def list_save_files() -> list[str]:
    return _list_save_files(SAVE_DIR)


def get_save_directory():
    return _get_save_directory(SAVE_DIR)


def save_uploaded_file(uploaded_file) -> str:
    return _save_uploaded_file(uploaded_file, SAVE_DIR)


def _factorio_command() -> list[str]:
    return _factorio_command_impl(INSTALL_DIR)


__all__ = [
    "ServerManager",
    "platform",
    "BASE_DIR",
    "CONFIG_PATH",
    "INSTALL_DIR",
    "LOG_DIR",
    "PID_PATH",
    "SAVE_DIR",
    "SERVER_SETTINGS_DIR",
    "SERVER_SETTINGS_PATH",
    "SERVER_SETTINGS_EXAMPLE_PATH",
    "INSTALL_PROGRESS_PATH",
    "DEFAULT_CONFIG",
    "DEFAULT_INSTALL_ARCHIVE",
    "DEFAULT_INSTALL_URL",
    "get_logs",
    "get_install_progress",
    "get_save_directory",
    "list_save_files",
    "load_server_config",
    "save_uploaded_file",
    "save_server_config",
    "load_server_settings",
    "save_server_settings",
    "build_server_settings_fields",
    "update_server_settings_from_form",
    "clear_logs",
    "clear_installation",
    "clear_install_progress",
    "set_install_error",
    "log_error",
    "is_server_installed",
    "is_platform_supported",
    "_read_pid",
    "_write_pid",
    "_clear_pid",
    "_is_process_running",
    "_factorio_command",
    "_get_server_log_file",
    "_get_factorio_generated_log_file",
    "_extract_archive",
    "RuntimeStartupBuilder",
]
