from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.config import ADMINLIST_PATH, BANLIST_PATH, BASE_DIR, WHITELIST_PATH
from backend.services.runtime_state_service import mark_pending

logger = logging.getLogger("fsm.services.access_control")


@dataclass
class AccessListStatus:
    name: str
    path: str
    exists: bool
    count: int
    records: list[str]
    valid: bool
    error: Optional[str] = None


def _read_json_file(path: Path) -> tuple[Optional[object], Optional[str]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"Unable to read file: {exc}"

    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"


def _read_adminlist(path: Path) -> AccessListStatus:
    data, error = _read_json_file(path)
    if error is not None:
        return AccessListStatus("admins", str(path), path.exists(), 0, [], False, error)
    if data is None:
        return AccessListStatus("admins", str(path), False, 0, [], True, None)

    if isinstance(data, dict):
        admins = data.get("admins", [])
    elif isinstance(data, list):
        admins = data
    else:
        return AccessListStatus(
            "admins", str(path), True, 0, [], False,
            "Expected an object with 'admins' or a list of names",
        )

    if not isinstance(admins, list) or not all(isinstance(a, str) for a in admins):
        return AccessListStatus(
            "admins", str(path), True, 0, [], False,
            "'admins' must be a list of strings",
        )

    return AccessListStatus("admins", str(path), True, len(admins), list(admins), True, None)


def _read_namelist(path: Path) -> AccessListStatus:
    data, error = _read_json_file(path)
    if error is not None:
        return AccessListStatus("names", str(path), path.exists(), 0, [], False, error)
    if data is None:
        return AccessListStatus("names", str(path), False, 0, [], True, None)

    if not isinstance(data, list) or not all(isinstance(n, str) for n in data):
        return AccessListStatus(
            "names", str(path), True, 0, [], False,
            "Expected a list of player names",
        )

    return AccessListStatus("names", str(path), True, len(data), list(data), True, None)


def _read_banlist(path: Path) -> AccessListStatus:
    data, error = _read_json_file(path)
    if error is not None:
        return AccessListStatus("bans", str(path), path.exists(), 0, [], False, error)
    if data is None:
        return AccessListStatus("bans", str(path), False, 0, [], True, None)

    names: list[str] = []
    valid = True
    error_msg: Optional[str] = None

    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, str):
                names.append(entry)
            elif isinstance(entry, dict):
                username = entry.get("username") or entry.get("name") or ""
                if username:
                    names.append(str(username))
            else:
                valid = False
                error_msg = "Ban entries must be strings or objects"
                break
    elif isinstance(data, dict):
        bans = data.get("bans", [])
        if isinstance(bans, list):
            for entry in bans:
                if isinstance(entry, str):
                    names.append(entry)
                elif isinstance(entry, dict):
                    username = entry.get("username") or entry.get("name") or ""
                    if username:
                        names.append(str(username))
                else:
                    valid = False
                    error_msg = "Ban entries must be strings or objects"
                    break
        else:
            valid = False
            error_msg = "'bans' must be a list"
    else:
        valid = False
        error_msg = "Expected a list of bans or an object with 'bans'"

    return AccessListStatus("bans", str(path), True, len(names), names, valid, error_msg)


def get_adminlist_status() -> AccessListStatus:
    return _read_adminlist(ADMINLIST_PATH)


def get_whitelist_status() -> AccessListStatus:
    status = _read_namelist(WHITELIST_PATH)
    # Whitelist specific behavior:
    # - enabled = file exists (even if empty)
    # - disabled = file does not exist
    # This matches Factorio dedicated server behavior where the mere presence
    # of server-whitelist.json enables the whitelist.
    if not status.exists and not status.error:
        return AccessListStatus(
            "whitelist",
            str(WHITELIST_PATH),
            False,
            0,
            [],
            True,
            None,
        )
    return status


def get_banlist_status() -> AccessListStatus:
    return _read_banlist(BANLIST_PATH)


def get_access_control_status() -> dict:
    return {
        "admins": _status_to_dict(get_adminlist_status()),
        "whitelist": _status_to_dict(get_whitelist_status()),
        "banlist": _status_to_dict(get_banlist_status()),
    }


def _status_to_dict(status: AccessListStatus) -> dict:
    return {
        "name": status.name,
        "path": status.path,
        "exists": status.exists,
        "count": status.count,
        "records": status.records,
        "valid": status.valid,
        "error": status.error,
    }


VALID_LIST_KEYS = ("admins", "whitelist", "banlist")


def _path_for_key(key: str) -> Path:
    if key == "admins":
        return ADMINLIST_PATH
    if key == "whitelist":
        return WHITELIST_PATH
    return BANLIST_PATH


def _serialize_records(key: str, records: list[str]) -> object:
    if key == "admins":
        return {"admins": records}
    return records


def _normalize_name(name: str) -> str:
    return (name or "").strip()


def add_to_list(key: str, name: str) -> dict:
    if key not in VALID_LIST_KEYS:
        raise ValueError(f"Unknown access control list: {key}")

    normalized = _normalize_name(name)
    if not normalized:
        raise ValueError("Name cannot be empty")

    path = _path_for_key(key)
    status = _read_current(key, path)
    if status.error is not None and status.exists:
        raise ValueError(status.error)

    records = status.records
    if normalized in records:
        raise ValueError(f"Duplicate entry: {normalized}")

    records = sorted(set(records) | {normalized})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_serialize_records(key, records), indent=2),
        encoding="utf-8",
    )
    logger.info("Added %s to %s", normalized, key)
    return _status_to_dict(get_status_for_key(key))


def remove_from_list(key: str, name: str) -> dict:
    if key not in VALID_LIST_KEYS:
        raise ValueError(f"Unknown access control list: {key}")

    normalized = _normalize_name(name)
    path = _path_for_key(key)
    status = _read_current(key, path)
    if status.error is not None and status.exists:
        raise ValueError(status.error)

    records = [r for r in status.records if r != normalized]
    if len(records) == len(status.records):
        raise ValueError(f"Entry not found: {normalized}")

    if records:
        path.write_text(
            json.dumps(_serialize_records(key, records), indent=2),
            encoding="utf-8",
        )
    else:
        path.unlink(missing_ok=True)
    logger.info("Removed %s from %s", normalized, key)
    return _status_to_dict(get_status_for_key(key))


def enable_whitelist() -> dict:
    WHITELIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not WHITELIST_PATH.exists():
        WHITELIST_PATH.write_text("[]", encoding="utf-8")
        logger.info("Enabled whitelist by creating %s", WHITELIST_PATH)
    mark_pending("whitelist")
    return _status_to_dict(get_whitelist_status())


def disable_whitelist() -> dict:
    if WHITELIST_PATH.exists():
        WHITELIST_PATH.unlink()
        logger.info("Disabled whitelist by removing %s", WHITELIST_PATH)
    mark_pending("whitelist")
    return _status_to_dict(get_whitelist_status())


def _read_current(key: str, path: Path) -> AccessListStatus:
    if key == "admins":
        return _read_adminlist(path)
    if key == "whitelist":
        return _read_namelist(path)
    return _read_banlist(path)


def get_status_for_key(key: str) -> AccessListStatus:
    if key == "admins":
        return get_adminlist_status()
    if key == "whitelist":
        return get_whitelist_status()
    return get_banlist_status()
