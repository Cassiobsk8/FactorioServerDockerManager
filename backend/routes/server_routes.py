from __future__ import annotations

import logging
import threading
from typing import Any

from backend.config import (
    BASE_DIR,
    CONFIG_PATH,
    DEFAULT_CONFIG,
    DEFAULT_INSTALL_ARCHIVE,
    DEFAULT_INSTALL_URL,
    INSTALL_DIR,
    INSTALL_PROGRESS_PATH,
    LOG_DIR,
    PID_PATH,
    SERVER_SETTINGS_PATH,
)
from backend.services.factorio_service import (
    FactorioService,
    _set_install_progress,
    clear_install_progress,
    get_install_progress,
    load_server_config,
    load_server_settings,
    log_error,
    save_server_config,
    save_server_settings,
    update_server_settings_from_form,
    build_server_settings_fields,
    get_logs,
    clear_logs,
    clear_installation,
    set_install_error,
)
from backend.services.save_service import list_save_files, get_active_save
from backend.services.settings_service import load_app_settings
from backend.version import APP_VERSION, RELEASE_NAME, BUILD_DATE
from flask import Blueprint, jsonify, redirect, render_template, request

logger = logging.getLogger("fsm.routes.server")

server_bp = Blueprint("server", __name__)

factorio_service = FactorioService()


@server_bp.route("/")
def home():
    config = load_server_config()
    server_settings = load_server_settings()
    install_progress = get_install_progress()
    install_status = (
        "installing"
        if install_progress.get("status") == "progress"
        else factorio_service.get_install_status()
    )
    server_settings_fields = build_server_settings_fields(server_settings)
    app_settings = load_app_settings()
    rcon_settings = {
        "host": app_settings.get("rcon_host", "127.0.0.1"),
        "port": app_settings.get("rcon_port", 27015),
        "timeout": app_settings.get("rcon_timeout", 5),
        "password": app_settings.get("rcon_password", ""),
        "configured": bool(app_settings.get("rcon_password")),
    }
    return render_template(
        "index.html",
        status=factorio_service.get_status(),
        logs=get_logs(),
        config=config,
        server_settings_fields=server_settings_fields,
        save_files=list_save_files(),
        active_save=get_active_save(),
        install_status=install_status,
        app_version=APP_VERSION,
        app_release_name=RELEASE_NAME,
        app_build_date=BUILD_DATE,
        language=app_settings.get("language", "en"),
        rcon_settings=rcon_settings,
    )


@server_bp.route("/status")
def status():
    install_progress = get_install_progress()
    return jsonify(
        {
            "status": factorio_service.get_status(),
            "install_status": (
                "installing"
                if install_progress.get("status") == "progress"
                else factorio_service.get_install_status()
            ),
        }
    )


@server_bp.route("/control/<action>", methods=["POST"])
def control(action: str):
    try:
        logger.info("control action requested: %s", action)
        if action == "start":
            factorio_service.start_server()
        elif action == "stop":
            factorio_service.stop_server()
        elif action == "restart":
            factorio_service.restart_server()
    except Exception as exc:
        logger.exception("Action %s failed", action)
        log_error(f"Action {action} failed: {exc}")
    return redirect("/")


@server_bp.route("/install", methods=["POST"])
def install():
    archive_path = request.form.get("archive_path", "").strip() or None
    try:
        factorio_service.install_server(archive_path=archive_path)
    except Exception as exc:
        log_error(f"Install failed: {exc}")
    return redirect("/")


@server_bp.route("/install/start", methods=["POST"])
def install_start():
    archive_path = request.form.get("archive_path", "").strip() or None
    progress = get_install_progress()
    if progress.get("status") == "progress":
        return jsonify({"error": "Installation already running."}), 409

    clear_install_progress()

    def run_install():
        try:
            logger.info("Starting server installation (archive: %s)", archive_path)
            factorio_service.install_server(archive_path=archive_path)
            logger.info("Server installation finished")
        except Exception as exc:
            logger.exception("Install failed")
            set_install_error(str(exc))
            log_error(f"Install failed: {exc}")

    thread = threading.Thread(target=run_install, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@server_bp.route("/install/progress")
def install_progress():
    return jsonify(get_install_progress())


@server_bp.route("/server-settings")
def server_settings_api():
    try:
        settings = load_server_settings()
        fields = build_server_settings_fields(settings)
        file_info: dict[str, Any] = {}
        try:
            settings_path = SERVER_SETTINGS_PATH
            file_exists = settings_path.exists()
            file_size = settings_path.stat().st_size if file_exists else 0
            raw_preview = settings_path.read_text(encoding="utf-8", errors="replace")[:512] if file_exists else ""
            file_info = {"exists": file_exists, "size": file_size, "preview": raw_preview}
        except Exception:
            file_info = {"exists": False, "size": 0, "preview": ""}

        logger.info(
            "/server-settings requested: fields=%d keys=%d file_exists=%s size=%d",
            len(fields),
            len(settings.keys() if isinstance(settings, dict) else []),
            file_info.get("exists"),
            file_info.get("size"),
        )
        return jsonify({"settings": settings, "fields": fields, "file_info": file_info})
    except Exception as exc:
        log_error(f"Failed to load server settings: {exc}")
        return jsonify({"settings": {}, "fields": []}), 500


@server_bp.route("/config", methods=["POST"])
def update_config():
    config = load_server_config()
    server_name = request.form.get("server_name", "").strip() or config["server_name"]
    server_password = request.form.get("server_password", "").strip() or config["server_password"]
    save_server_config(values={"server_name": server_name, "server_password": server_password})

    current_settings = load_server_settings()
    updated_settings = update_server_settings_from_form(request.form, current_settings)
    save_server_settings(updated_settings)

    return redirect("/")


@server_bp.route("/logs/data")
def logs_data():
    return jsonify({"logs": get_logs()})


@server_bp.route("/logs/clear", methods=["POST"])
def clear_log_route():
    try:
        clear_logs()
    except Exception as exc:
        log_error(f"Clear logs failed: {exc}")
    return redirect("/")


@server_bp.route("/install/clear", methods=["POST"])
def clear_installation_route():
    try:
        clear_installation()
    except Exception as exc:
        log_error(f"Clear installation failed: {exc}")
    return redirect("/")


@server_bp.route("/health")
def health():
    return {"status": "ok"}


def register_server_routes(app):
    app.register_blueprint(server_bp)
