from __future__ import annotations

import logging

from backend.services import access_control_service
from flask import Blueprint, jsonify, request

logger = logging.getLogger("fsm.routes.access_control")

access_control_bp = Blueprint("access_control", __name__)

VALID_LIST_KEYS = ("admins", "whitelist", "banlist")


@access_control_bp.route("/api/access-control", methods=["GET"])
def api_access_control():
    try:
        return jsonify(access_control_service.get_access_control_status())
    except Exception as exc:
        logger.exception("Failed to read access control lists")
        return jsonify({"error": str(exc)}), 500


@access_control_bp.route("/api/access-control/<list_key>", methods=["POST"])
def api_access_control_add(list_key: str):
    if list_key not in VALID_LIST_KEYS:
        return jsonify({"error": f"Unknown list: {list_key}"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        status = access_control_service.add_to_list(list_key, name)
        return jsonify({list_key: status})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to add to %s", list_key)
        return jsonify({"error": str(exc)}), 500


@access_control_bp.route("/api/access-control/<list_key>", methods=["DELETE"])
def api_access_control_remove(list_key: str):
    if list_key not in VALID_LIST_KEYS:
        return jsonify({"error": f"Unknown list: {list_key}"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        status = access_control_service.remove_from_list(list_key, name)
        return jsonify({list_key: status})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to remove from %s", list_key)
        return jsonify({"error": str(exc)}), 500


@access_control_bp.route("/api/access-control/whitelist/enable", methods=["POST"])
def api_access_control_whitelist_enable():
    try:
        status = access_control_service.enable_whitelist()
        return jsonify({"whitelist": status})
    except Exception as exc:
        logger.exception("Failed to enable whitelist")
        return jsonify({"error": str(exc)}), 500


@access_control_bp.route("/api/access-control/whitelist/disable", methods=["DELETE"])
def api_access_control_whitelist_disable():
    try:
        status = access_control_service.disable_whitelist()
        return jsonify({"whitelist": status})
    except Exception as exc:
        logger.exception("Failed to disable whitelist")
        return jsonify({"error": str(exc)}), 500


def register_access_control_routes(app):
    app.register_blueprint(access_control_bp)
