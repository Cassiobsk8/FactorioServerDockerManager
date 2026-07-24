from __future__ import annotations

import logging
from pathlib import Path

from backend.config import BASE_DIR
from backend.services.world_builder_service import (
    create_world,
    generate_preview,
    list_planets,
    PREVIEWS_DIR,
    WorldConfig,
    _compute_config_hash,
    validate_factorio_binary,
)
from flask import Blueprint, jsonify, request, send_from_directory

logger = logging.getLogger("fsm.routes.world_builder")

world_builder_bp = Blueprint("world_builder", __name__)


@world_builder_bp.route("/api/world-builder/config-hash", methods=["POST"])
def api_world_builder_config_hash():
    try:
        data = request.get_json(silent=True) or {}
        config = WorldConfig(
            world_name=data.get("world_name", ""),
            seed=data.get("seed"),
            random_seed=data.get("random_seed", True),
            planet=data.get("planet", "nauvis"),
            settings=data.get("settings", {}),
            map_settings=data.get("map_settings", {}),
        )
        config_hash = _compute_config_hash(config)
        return jsonify({"config_hash": config_hash})
    except Exception as exc:
        logger.exception("Failed to compute config hash")
        return jsonify({"error": str(exc)}), 500


@world_builder_bp.route("/api/world-builder/options")
def api_world_builder_options():
    try:
        return jsonify(
            {
                "planets": list_planets(),
            }
        )
    except Exception as exc:
        logger.exception("Failed to load world builder options")
        return jsonify({"error": str(exc)}), 500


@world_builder_bp.route("/api/world-builder/status")
def api_world_builder_status():
    try:
        validation = validate_factorio_binary()
        return jsonify(validation)
    except Exception as exc:
        logger.exception("Unexpected error validating Factorio binary")
        return jsonify({"valid": False, "reason": "error", "message": str(exc)}), 500


@world_builder_bp.route("/api/world-builder/preview", methods=["POST"])
def api_world_builder_preview():
    try:
        data = request.get_json(silent=True) or {}
        config = WorldConfig(
            world_name=data.get("world_name", ""),
            seed=data.get("seed"),
            random_seed=data.get("random_seed", True),
            planet=data.get("planet", "nauvis"),
            settings=data.get("settings", {}),
            map_settings=data.get("map_settings", {}),
        )
        errors = config.validate()
        if errors:
            return jsonify({"error": "validation_failed", "errors": errors}), 400

        result = generate_preview(config)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        logger.exception("Preview generation failed")
        return jsonify({"error": str(exc)}), 500


@world_builder_bp.route("/api/world-builder/create", methods=["POST"])
def api_world_builder_create():
    try:
        data = request.get_json(silent=True) or {}
        config = WorldConfig(
            world_name=data.get("world_name", ""),
            seed=data.get("seed"),
            random_seed=data.get("random_seed", True),
            planet=data.get("planet", "nauvis"),
            settings=data.get("settings", {}),
            map_settings=data.get("map_settings", {}),
        )
        preview_hash = data.get("preview_hash")

        errors = config.validate()
        if errors:
            return jsonify({"error": "validation_failed", "errors": errors}), 400

        if not preview_hash:
            return jsonify({"error": "preview_hash is required"}), 400

        result = create_world(config, preview_hash)
        return jsonify(result), 201
    except FileExistsError as exc:
        return jsonify({"error": str(exc)}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        logger.exception("World creation failed")
        return jsonify({"error": str(exc)}), 500


@world_builder_bp.route("/api/world-builder/preview-image/<preview_hash>")
def api_world_builder_preview_image(preview_hash: str):
    try:
        normalized_hash = preview_hash.removesuffix(".png")
        preview_file = PREVIEWS_DIR / f"{normalized_hash}.png"
        logger.info(
            "DIAGNOSTIC preview-image route: preview_hash=%s normalized_hash=%s path=%s exists=%s",
            preview_hash,
            normalized_hash,
            preview_file,
            preview_file.exists(),
        )
        if PREVIEWS_DIR.exists():
            logger.debug(
                "DIAGNOSTIC preview-image route files: preview_hash=%s files=%s",
                preview_hash,
                sorted(p.name for p in PREVIEWS_DIR.iterdir()),
            )
        if not preview_file.exists():
            return jsonify({"error": "preview not found"}), 404
        return send_from_directory(
            PREVIEWS_DIR,
            f"{normalized_hash}.png",
            mimetype="image/png",
            as_attachment=False,
        )
    except Exception as exc:
        logger.exception("Failed to serve preview image")
        return jsonify({"error": str(exc)}), 500


def register_world_builder_routes(app):
    app.register_blueprint(world_builder_bp)
