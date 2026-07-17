from __future__ import annotations

import logging
from typing import Any, Dict

from backend.services import rcon_service
from backend.services.rcon_service import (
    RconAuthError,
    RconConnectionError,
    RconNotConfiguredError,
    RconTimeoutError,
    apply_rcon_settings,
    get_rcon_service,
    get_rcon_players,
    get_rcon_status,
    reset_rcon_service,
    test_rcon_connection,
)
from flask import Blueprint, jsonify, request

logger = logging.getLogger("fsm.routes.rcon")

rcon_bp = Blueprint("rcon", __name__)


def _safe_str(value: Any, default: str = "") -> str:
    return "" if value is None else str(value)


@rcon_bp.route("/api/rcon/status")
def api_rcon_status():
    try:
        status = get_rcon_status()
        logger.info("RCON status: connected=%s players=%s error=%s", status.get("connected"), status.get("player_count"), status.get("error"))
        return jsonify(status)
    except Exception as exc:
        logger.exception("RCON status failed")
        return jsonify({"connected": False, "error": str(exc)}), 500


@rcon_bp.route("/api/rcon/players")
def api_rcon_players():
    try:
        players = get_rcon_players()
        return jsonify(players)
    except Exception as exc:
        logger.exception("RCON players failed")
        return jsonify({"connected": False, "players": [], "error": str(exc)}), 500


@rcon_bp.route("/api/rcon/test", methods=["POST"])
def api_rcon_test():
    data = request.get_json(silent=True) or {}
    host = _safe_str(data.get("host")).strip() or None
    port_raw = _safe_str(data.get("port")).strip()
    password = _safe_str(data.get("password"))
    timeout_raw = _safe_str(data.get("timeout")).strip()

    port = int(port_raw) if port_raw else None
    timeout = int(timeout_raw) if timeout_raw else None

    try:
        result = test_rcon_connection(host=host, port=port, password=password, timeout=timeout)
        return jsonify(result)
    except Exception as exc:
        logger.exception("RCON test failed")
        return jsonify({"connected": False, "error": str(exc)}), 500


@rcon_bp.route("/api/rcon/command", methods=["POST"])
def api_rcon_command():
    data = request.get_json(silent=True) or {}
    command = _safe_str(data.get("command")).strip()
    if not command:
        return jsonify({"error": "command required"}), 400

    try:
        service = get_rcon_service()
    except RconNotConfiguredError as exc:
        logger.warning("RCON command not configured: %s", exc)
        return jsonify({"error": str(exc), "connected": False}), 400

    try:
        logger.info("RCON API command: %r", command)
        response = service.execute_command(command)
        logger.info("RCON API response len=%s for command=%r", len(response), command)
        return jsonify({"response": response, "connected": True})
    except RconConnectionError as exc:
        logger.warning("RCON API connection error for command=%r: %s", command, exc)
        return jsonify({"error": str(exc), "connected": False}), 503
    except RconTimeoutError as exc:
        logger.warning("RCON API timeout for command=%r: %s", command, exc)
        return jsonify({"error": str(exc), "connected": False}), 504
    except RconAuthError as exc:
        logger.warning("RCON API auth error for command=%r: %s", command, exc)
        return jsonify({"error": str(exc), "connected": False}), 401
    except Exception as exc:
        logger.exception("RCON command failed for command=%r", command)
        return jsonify({"error": str(exc), "connected": False}), 500


@rcon_bp.route("/api/rcon/save", methods=["POST"])
def api_rcon_save():
    try:
        service = get_rcon_service()
    except RconNotConfiguredError as exc:
        return jsonify({"error": str(exc), "connected": False}), 400
    try:
        response = service.save_game()
        return jsonify({"response": response, "connected": True})
    except RconConnectionError as exc:
        return jsonify({"error": str(exc), "connected": False}), 503
    except RconTimeoutError as exc:
        return jsonify({"error": str(exc), "connected": False}), 504
    except RconAuthError as exc:
        return jsonify({"error": str(exc), "connected": False}), 401
    except Exception as exc:
        logger.exception("RCON save failed")
        return jsonify({"error": str(exc), "connected": False}), 500


@rcon_bp.route("/api/rcon/broadcast", methods=["POST"])
def api_rcon_broadcast():
    data = request.get_json(silent=True) or {}
    message = _safe_str(data.get("message")).strip()
    if not message:
        return jsonify({"error": "message required"}), 400

    try:
        service = get_rcon_service()
    except RconNotConfiguredError as exc:
        return jsonify({"error": str(exc), "connected": False}), 400

    try:
        response = service.broadcast_message(message)
        return jsonify({"response": response, "connected": True})
    except RconConnectionError as exc:
        return jsonify({"error": str(exc), "connected": False}), 503
    except RconTimeoutError as exc:
        return jsonify({"error": str(exc), "connected": False}), 504
    except RconAuthError as exc:
        return jsonify({"error": str(exc), "connected": False}), 401
    except Exception as exc:
        logger.exception("RCON broadcast failed")
        return jsonify({"error": str(exc), "connected": False}), 500


@rcon_bp.route("/api/rcon/settings", methods=["GET"])
def api_rcon_settings_get():
    from backend.services.settings_service import load_app_settings

    settings = load_app_settings()
    return jsonify(
        {
            "host": settings.get("rcon_host", "127.0.0.1"),
            "port": settings.get("rcon_port", 27015),
            "timeout": settings.get("rcon_timeout", 5),
            "password": settings.get("rcon_password", ""),
            "configured": bool(settings.get("rcon_password")),
        }
    )


@rcon_bp.route("/api/rcon/settings", methods=["POST"])
def api_rcon_settings_post():
    data = request.get_json(silent=True) or {}
    host = _safe_str(data.get("host")).strip()
    port_raw = _safe_str(data.get("port")).strip()
    password = _safe_str(data.get("password"))
    timeout_raw = _safe_str(data.get("timeout")).strip()

    if not port_raw:
        return jsonify({"error": "port required"}), 400

    try:
        port = int(port_raw)
    except ValueError:
        return jsonify({"error": "port must be an integer"}), 400

    timeout = int(timeout_raw) if timeout_raw else 5

    try:
        result = apply_rcon_settings(host=host, port=port, password=password, timeout=timeout)
        reset_rcon_service()
        return jsonify(
            {
                "host": result.get("rcon_host"),
                "port": result.get("rcon_port"),
                "timeout": result.get("rcon_timeout"),
                "configured": bool(result.get("rcon_password")),
            }
        )
    except Exception as exc:
        logger.exception("RCON settings save failed")
        return jsonify({"error": str(exc)}), 500


def register_rcon_routes(app):
    app.register_blueprint(rcon_bp)
