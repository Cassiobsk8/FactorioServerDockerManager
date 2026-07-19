from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import APP_SETTINGS_PATH, DEFAULT_APP_SETTINGS, PLAYER_DATA_PATH

logger = logging.getLogger("fsm.services.factorio")

FACTORIO_USERNAME_KEY = "factorio_username"
FACTORIO_TOKEN_KEY = "factorio_service_token"
PLAYER_DATA_USERNAME_KEY = "service-username"
PLAYER_DATA_TOKEN_KEY = "service-token"


def _mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return token[:4] + "****"
    return token[:4] + "****" + token[-4:]


def _read_settings() -> Dict[str, Any]:
    if not APP_SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(APP_SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception as exc:
        logger.exception("Failed to load factorio services settings")
        return {}


def _write_settings(data: Dict[str, Any]) -> None:
    APP_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_factorio_services() -> Dict[str, str]:
    data = _read_settings()
    nested = data.get("factorio_services", {})
    if isinstance(nested, dict):
        return {
            FACTORIO_USERNAME_KEY: nested.get(FACTORIO_USERNAME_KEY, ""),
            FACTORIO_TOKEN_KEY: nested.get(FACTORIO_TOKEN_KEY, ""),
        }
    return {
        FACTORIO_USERNAME_KEY: data.get(FACTORIO_USERNAME_KEY, DEFAULT_APP_SETTINGS.get(FACTORIO_USERNAME_KEY, "")),
        FACTORIO_TOKEN_KEY: data.get(FACTORIO_TOKEN_KEY, DEFAULT_APP_SETTINGS.get(FACTORIO_TOKEN_KEY, "")),
    }


def save_factorio_services(username: str, token: str) -> Dict[str, str]:
    data = _read_settings()
    data.setdefault("factorio_services", {})
    data["factorio_services"][FACTORIO_USERNAME_KEY] = username or ""
    data["factorio_services"][FACTORIO_TOKEN_KEY] = token or ""
    data[FACTORIO_USERNAME_KEY] = username or ""
    data[FACTORIO_TOKEN_KEY] = token or ""
    _write_settings(data)
    return {
        FACTORIO_USERNAME_KEY: username or "",
        FACTORIO_TOKEN_KEY: _mask_token(token or ""),
    }


def get_factorio_services_status() -> Dict[str, Any]:
    data = load_factorio_services()
    username = data.get(FACTORIO_USERNAME_KEY, "")
    token = data.get(FACTORIO_TOKEN_KEY, "")

    if not username or not token:
        return {
            "status": "not_configured",
            "username": username,
            "token_masked": "",
        }

    token_masked = _mask_token(token)
    if not re.match(r'^[A-Za-z0-9]+$', token):
        return {
            "status": "invalid",
            "username": username,
            "token_masked": token_masked,
        }

    return {
        "status": "authenticated",
        "username": username,
        "token_masked": token_masked,
    }


def validate_factorio_services() -> Dict[str, Any]:
    data = load_factorio_services()
    username = data.get(FACTORIO_USERNAME_KEY, "")
    token = data.get(FACTORIO_TOKEN_KEY, "")

    errors = []
    if not username:
        errors.append("username is required")
    if not token:
        errors.append("token is required")
    elif not re.match(r'^[A-Za-z0-9]+$', token):
        errors.append("token must be alphanumeric")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "username": username}


def serialize_factorio_services() -> Dict[str, str]:
    data = load_factorio_services()
    username = data.get(FACTORIO_USERNAME_KEY, "")
    token = data.get(FACTORIO_TOKEN_KEY, "")
    return {
        PLAYER_DATA_USERNAME_KEY: username,
        PLAYER_DATA_TOKEN_KEY: token,
    }


def write_player_data() -> Dict[str, Any]:
    data = load_factorio_services()
    username = data.get(FACTORIO_USERNAME_KEY, "")
    token = data.get(FACTORIO_TOKEN_KEY, "")

    if not username or not token:
        return {"written": False, "reason": "not_configured"}

    player_data = {
        PLAYER_DATA_USERNAME_KEY: username,
        PLAYER_DATA_TOKEN_KEY: token,
    }
    PLAYER_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAYER_DATA_PATH.write_text(json.dumps(player_data, indent=2), encoding="utf-8")
    return {"written": True, "path": str(PLAYER_DATA_PATH)}


def load_player_data() -> Dict[str, str]:
    if not PLAYER_DATA_PATH.exists():
        return {}
    try:
        data = json.loads(PLAYER_DATA_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {
            PLAYER_DATA_USERNAME_KEY: data.get(PLAYER_DATA_USERNAME_KEY, ""),
            PLAYER_DATA_TOKEN_KEY: data.get(PLAYER_DATA_TOKEN_KEY, ""),
        }
    except Exception as exc:
        logger.exception("Failed to load player data")
        return {}
