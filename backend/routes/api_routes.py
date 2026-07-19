from __future__ import annotations

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from backend.config import BASE_DIR

from backend.services.factorio_service import (
    FactorioService,
    get_install_progress,
    get_logs,
    load_server_config,
    load_server_settings,
    save_server_config,
    log_error,
    _factorio_command as _factorio_command_impl,
)
from backend.services.factorio_services_service import (
    get_factorio_services_status,
    save_factorio_services,
)
from backend.services.metrics_service import get_factorio_version, get_process_metrics
from backend.services.save_service import load_active_save, get_save_info
from backend.services.settings_service import load_app_settings, save_app_settings
from backend.services.runtime_state_service import get_runtime_state, clear_pending, mark_pending, remove_pending
from backend.services.startup_validation_service import validate_startup
from backend.version import APP_VERSION, RELEASE_NAME, BUILD_DATE
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
    runtime_state = get_runtime_state()
    factorio_services = get_factorio_services_status()
    return jsonify(
        {
            "status": factorio_service.get_status(),
            "runtime_state": runtime_state,
            "factorio_account": factorio_services,
            "server": {
                "install_status": (
                    "installing"
                    if install_progress.get("status") == "progress"
                    else factorio_service.get_install_status()
                ),
                "cpu_percent": metrics.get("cpu_percent", 0.0),
                "ram_used_mb": metrics.get("ram_used_mb", 0),
                "ram_total_mb": metrics.get("ram_total_mb", 0),
                "uptime_seconds": metrics.get("uptime_seconds", 0),
                "disk_used_mb": metrics.get("disk_used_mb", 0),
                "disk_total_mb": metrics.get("disk_total_mb", 0),
                "factorio_version": get_factorio_version(),
                "active_save": _build_active_save_payload(),
            },
            "version": APP_VERSION,
            "release_name": RELEASE_NAME,
            "build_date": BUILD_DATE,
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
        clear_pending()
        return jsonify({"status": "restarted"})
    except Exception as exc:
        logger.exception("API restart failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/validate-startup", methods=["POST"])
def api_validate_startup():
    try:
        result = validate_startup()
        return jsonify(result)
    except Exception as exc:
        logger.exception("Startup validation failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/runtime-state")
def api_runtime_state():
    try:
        return jsonify(get_runtime_state())
    except Exception as exc:
        logger.exception("Failed to load runtime state")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/runtime-state/clear", methods=["POST"])
def api_runtime_state_clear():
    try:
        return jsonify(clear_pending())
    except Exception as exc:
        logger.exception("Failed to clear runtime state")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/runtime-state/<key>", methods=["DELETE"])
def api_runtime_state_remove(key):
    try:
        return jsonify(remove_pending(key))
    except Exception as exc:
        logger.exception("Failed to remove pending change %s", key)
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/startup-preview")
def api_startup_preview():
    try:
        cmd = _factorio_command_impl()
        masked = [
            part if not part.startswith("--rcon-password=") else "--rcon-password=******"
            for part in cmd
        ]
        return jsonify({"command": masked})
    except Exception as exc:
        logger.exception("Startup preview failed")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/factorio-services", methods=["GET"])
def api_factorio_services_get():
    try:
        return jsonify(get_factorio_services_status())
    except Exception as exc:
        logger.exception("Failed to load factorio services")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/factorio-services", methods=["POST"])
def api_factorio_services_save():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    token = (data.get("token") or "").strip()
    if not username or not token:
        return jsonify({"error": "username and token are required"}), 400
    try:
        result = save_factorio_services(username, token)
        mark_pending("factorio_services", "Factorio Account")
        return jsonify(result)
    except Exception as exc:
        logger.exception("Failed to save factorio services")
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/api/rcon", methods=["POST"])
def api_rcon():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "command required"}), 400

    from backend.services.rcon_service import (
        RconAuthError,
        RconConnectionError,
        RconNotConfiguredError,
        RconTimeoutError,
        get_rcon_service,
    )

    try:
        service = get_rcon_service()
        response = service.execute_command(command)
        return jsonify({"response": response, "connected": True})
    except (RconConnectionError, RconTimeoutError, RconAuthError) as exc:
        return jsonify({"error": str(exc), "connected": False}), 503
    except Exception as exc:
        logger.exception("RCON command failed")
        return jsonify({"error": str(exc), "connected": False}), 500


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


SUPPORTED_LANGS = {"en", "pt_BR", "es", "zh_CN"}


@api_bp.route("/api/translations/<lang>")
def api_translations(lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    try:
        path = BASE_DIR / "frontend" / "i18n" / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as exc:
        logger.exception("Failed to load translations for %s", lang)
        return jsonify({}), 500


@api_bp.route("/api/server-name", methods=["POST"])
def api_server_name():
    data = request.get_json(silent=True) or {}
    name = (data.get("server_name") or "").strip()
    if not name:
        return jsonify({"error": "server_name required"}), 400
    updated = save_server_config(values={"server_name": name})
    return jsonify({"server_name": updated.get("server_name", name)})


@api_bp.route("/api/settings", methods=["GET"])
def api_settings_get():
    return jsonify(load_app_settings())


@api_bp.route("/api/settings", methods=["POST"])
def api_settings_post():
    data = request.get_json(silent=True) or {}
    language = data.get("language")
    if language and language not in SUPPORTED_LANGS:
        language = "en"
    updated = save_app_settings({"language": language} if language else data)
    return jsonify(updated)


def register_api_routes(app):
    app.register_blueprint(api_bp)


def _build_active_save_payload():
    active_path = load_active_save()
    if not active_path:
        return None
    try:
        info = get_save_info(active_path.name)
        return {
            "name": info["name"],
            "size": info["size"],
            "modified": info["modified"],
        }
    except Exception:
        return {"name": active_path.name, "size": None, "modified": None}
