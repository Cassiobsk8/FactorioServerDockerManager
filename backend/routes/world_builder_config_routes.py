from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from backend.services.world_builder_config_engine import (
    get_default_values,
    get_form_config,
    serialize_form_values,
    validate_form_value,
)

logger = logging.getLogger("fsm.routes.world_builder_config")

world_builder_config_bp = Blueprint("world_builder_config", __name__)


@world_builder_config_bp.route("/api/world-builder/config-engine")
def api_world_builder_config_engine():
    try:
        source_file = request.args.get("source_file")
        config = get_form_config(source_file=source_file)
        return jsonify(config)
    except Exception as exc:
        logger.exception("Failed to load config engine metadata")
        return jsonify({"error": str(exc)}), 500


@world_builder_config_bp.route("/api/world-builder/serialize-config", methods=["POST"])
def api_world_builder_serialize_config():
    try:
        payload = request.get_json(silent=True) or {}
        values = payload.get("values", {})
        source_file = payload.get("source_file")
        result = serialize_form_values(values, source_file=source_file)
        return jsonify({"data": result})
    except Exception as exc:
        logger.exception("Failed to serialize config")
        return jsonify({"error": str(exc)}), 500


@world_builder_config_bp.route("/api/world-builder/deserialize-config", methods=["POST"])
def api_world_builder_deserialize_config():
    try:
        payload = request.get_json(silent=True) or {}
        data = payload.get("data", {})
        source_file = payload.get("source_file")
        result = deserialize_form_values(data, source_file=source_file)
        return jsonify({"values": result})
    except Exception as exc:
        logger.exception("Failed to deserialize config")
        return jsonify({"error": str(exc)}), 500


@world_builder_config_bp.route("/api/world-builder/default-config")
def api_world_builder_default_config():
    try:
        source_file = request.args.get("source_file")
        defaults = get_default_values(source_file=source_file)
        return jsonify({"values": defaults})
    except Exception as exc:
        logger.exception("Failed to load default config")
        return jsonify({"error": str(exc)}), 500


@world_builder_config_bp.route("/api/world-builder/validate-field", methods=["POST"])
def api_world_builder_validate_field():
    try:
        payload = request.get_json(silent=True) or {}
        field_id = payload.get("field_id")
        value = payload.get("value")
        if field_id is None:
            return jsonify({"error": "field_id is required"}), 400
        error = validate_form_value(field_id, value)
        return jsonify({"field_id": field_id, "valid": error is None, "error": error})
    except Exception as exc:
        logger.exception("Failed to validate field")
        return jsonify({"error": str(exc)}), 500


def register_world_builder_config_routes(app):
    app.register_blueprint(world_builder_config_bp)
