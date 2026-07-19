from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("fsm.runtime")

RUNTIME_STATE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "runtime_state.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_state() -> Dict[str, Any]:
    if not RUNTIME_STATE_PATH.exists():
        return {"pending": {}}
    try:
        return json.loads(RUNTIME_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"pending": {}}


def _write_state(state: Dict[str, Any]) -> None:
    _ensure_parent(RUNTIME_STATE_PATH)
    RUNTIME_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_runtime_state() -> Dict[str, Any]:
    state = _read_state()
    pending = state.get("pending", {})
    return {
        "pending": pending,
        "has_pending": bool(pending),
        "pending_keys": sorted(pending.keys()),
    }


def mark_pending(key: str) -> Dict[str, Any]:
    state = _read_state()
    pending = state.setdefault("pending", {})
    pending[key] = {
        "changed_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_state(state)
    logger.info("Marked %s as pending restart", key)
    return get_runtime_state()


def clear_pending() -> Dict[str, Any]:
    state = _read_state()
    state["pending"] = {}
    _write_state(state)
    logger.info("Cleared pending runtime state")
    return get_runtime_state()


def is_pending(key: str) -> bool:
    state = _read_state()
    return key in state.get("pending", {})
