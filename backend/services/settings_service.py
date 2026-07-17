from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.config import APP_SETTINGS_PATH, DEFAULT_APP_SETTINGS

logger = logging.getLogger("fsm.services.settings")


def load_app_settings() -> dict[str, str]:
    if not APP_SETTINGS_PATH.exists():
        return dict(DEFAULT_APP_SETTINGS)
    try:
        data = json.loads(APP_SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULT_APP_SETTINGS)
        return {**DEFAULT_APP_SETTINGS, **data}
    except Exception as exc:
        logger.exception("Failed to load app settings")
        return dict(DEFAULT_APP_SETTINGS)


def save_app_settings(values: dict[str, str]) -> dict[str, str]:
    current = load_app_settings()
    current.update({k: v for k, v in values.items() if v is not None})
    APP_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current
