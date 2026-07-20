from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.config import (
    ADMINLIST_PATH,
    BANLIST_PATH,
    SERVER_SETTINGS_PATH,
    WHITELIST_PATH,
)
from backend.services.access_control_service import _read_json_file
from backend.services.save_service import load_active_save

logger = logging.getLogger("fsm.validation")


class StartupValidationError:
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class StartupValidationWarning:
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


def _validate_active_save() -> Optional[StartupValidationError]:
    save = load_active_save()
    if save is None:
        return StartupValidationError(
            "no_active_save",
            "No active save configured. Create a new world, upload a save, or select an existing save before starting the server.",
        )
    return None


def _validate_server_settings() -> Optional[StartupValidationError]:
    if not SERVER_SETTINGS_PATH.exists():
        return StartupValidationError(
            "server_settings_missing",
            "server-settings.json is missing. Configure server settings before starting.",
        )
    return None


def _warn_rcon_password() -> Optional[StartupValidationWarning]:
    from backend.services.settings_service import load_app_settings

    app_settings = load_app_settings()
    password = app_settings.get("rcon_password", "")
    if not password:
        return StartupValidationWarning(
            "rcon_password_missing",
            "RCON password is not configured. The server will start without RCON. "
            "Set a password in Settings to enable remote console access.",
        )
    return None


def _validate_whitelist() -> Optional[StartupValidationError]:
    if not WHITELIST_PATH.exists():
        return None
    data, error = _read_json_file(WHITELIST_PATH)
    if error:
        return StartupValidationError(
            "whitelist_invalid",
            f"Whitelist file is invalid: {error}",
        )
    if data is None:
        return StartupValidationError(
            "whitelist_invalid",
            "Whitelist file is empty or unreadable.",
        )
    if not isinstance(data, list):
        return StartupValidationError(
            "whitelist_invalid",
            "Whitelist must be a list of player names.",
        )
    return None


def _validate_adminlist() -> Optional[StartupValidationError]:
    if not ADMINLIST_PATH.exists():
        return None
    data, error = _read_json_file(ADMINLIST_PATH)
    if error:
        return StartupValidationError(
            "adminlist_invalid",
            f"Adminlist file is invalid: {error}",
        )
    if data is None:
        return StartupValidationError(
            "adminlist_invalid",
            "Adminlist file is empty or unreadable.",
        )
    if isinstance(data, dict):
        admins = data.get("admins", [])
    elif isinstance(data, list):
        admins = data
    else:
        return StartupValidationError(
            "adminlist_invalid",
            "Adminlist must be an object with 'admins' or a list of names.",
        )
    if not isinstance(admins, list) or not all(isinstance(a, str) for a in admins):
        return StartupValidationError(
            "adminlist_invalid",
            "'admins' must be a list of strings.",
        )
    return None


def _validate_banlist() -> Optional[StartupValidationError]:
    if not BANLIST_PATH.exists():
        return None
    data, error = _read_json_file(BANLIST_PATH)
    if error:
        return StartupValidationError(
            "banlist_invalid",
            f"Banlist file is invalid: {error}",
        )
    if data is None:
        return StartupValidationError(
            "banlist_invalid",
            "Banlist file is empty or unreadable.",
        )
    if isinstance(data, dict):
        bans = data.get("bans", [])
    elif isinstance(data, list):
        bans = data
    else:
        return StartupValidationError(
            "banlist_invalid",
            "Banlist must be an object with 'bans' or a list of entries.",
        )
    if not isinstance(bans, list):
        return StartupValidationError(
            "banlist_invalid",
            "'bans' must be a list.",
        )
    return None


def validate_startup() -> dict:
    errors = []
    warnings = []

    for validator in (
        _validate_active_save,
        _validate_server_settings,
        _validate_whitelist,
        _validate_adminlist,
        _validate_banlist,
    ):
        result = validator()
        if result:
            errors.append(result.to_dict())

    rcon_warning = _warn_rcon_password()
    if rcon_warning:
        warnings.append(rcon_warning.to_dict())

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}
    return {"valid": True, "errors": [], "warnings": warnings}
