from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.services.factorio_service import (
    FactorioService,
    get_install_progress,
    get_logs,
    load_server_settings,
    log_error,
)
from backend.services.metrics_service import get_factorio_version, get_process_metrics
from backend.services.save_service import load_active_save
from flask import Blueprint, jsonify, request

logger = logging.getLogger("fsm.routes.api")

api_bp = Blueprint("api", __name__)

factorio_service = FactorioService()


@api_bp.route("/api/status")
def api_status():
    try:
        pid_path = Path(__file__).resolve().parent.parent.parent / "backend" / "server.pid"
        pid = None
        if pid_path.exists():
            pid = int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        pid = None

    metrics = get_process_metrics(pid)
    install_progress = get_install_progress()
    return jsonify(
        {
            "status": factorio_service.get_status(),
            "server": {
                "install_status": (
                    "installing"
                    if install_progress.get("status") == "progress"
                    else factorio_service.get_install_status()
                ),
                "cpu_percent": metrics.get("cpu_percent", 0.0),
                "ram_mb": metrics.get("ram_mb", 0),
                "uptime_seconds": metrics.get("uptime_seconds", 0),
                "disk_usage_mb": metrics.get("disk_usage_mb", 0),
                "factorio_version": get_factorio_version(),
                "active_save": load_active_save().name if load_active_save() else None,
            },
        }
    )


@api_bp.route("/api/logs")
def api_logs():
    return jsonify({"logs": get_logs()})


@api_bp.route("/api/start", methods=["POST"])
def api_start():
    try:
        factorio_service.start_server()
        return jsonify({"status": "started"})
    except Exception as exc:
        logger.exception("API start failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/stop", methods=["POST"])
def api_stop():
    try:
        factorio_service.stop_server()
        return jsonify({"status": "stopped"})
    except Exception as exc:
        logger.exception("API stop failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/restart", methods=["POST"])
def api_restart():
    try:
        factorio_service.restart_server()
        return jsonify({"status": "restarted"})
    except Exception as exc:
        logger.exception("API restart failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/rcon", methods=["POST"])
def api_rcon():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "command required"}), 400

    from backend.services.rcon_service import send_rcon_command
    try:
        response = send_rcon_command(command)
        return jsonify({"response": response})
    except Exception as exc:
        logger.exception("RCON command failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/mods", methods=["GET"])
def api_mods_list():
    return jsonify({"mods": [], "message": "Mod service not yet implemented"})


@api_bp.route("/api/mod/install", methods=["POST"])
def api_mod_install():
    return jsonify({"error": "Mod service not yet implemented"}), 501


@api_bp.route("/api/mod/remove", methods=["POST"])
def api_mod_remove():
    return jsonify({"error": "Mod service not yet implemented"}), 501


@api_bp.route("/api/backups", methods=["GET"])
def api_backups_list():
    return jsonify({"backups": [], "message": "Backup service not yet implemented"})


@api_bp.route("/api/backup/create", methods=["POST"])
def api_backup_create():
    return jsonify({"error": "Backup service not yet implemented"}), 501


@api_bp.route("/api/backup/restore", methods=["POST"])
def api_backup_restore():
    return jsonify({"error": "Backup service not yet implemented"}), 501


@api_bp.route("/api/backup/delete", methods=["POST"])
def api_backup_delete():
    return jsonify({"error": "Backup service not yet implemented"}), 501


def register_api_routes(app):
    app.register_blueprint(api_bp)
