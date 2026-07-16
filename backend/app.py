import sys
import threading
import logging
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# logging to stdout for terminal visibility
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger.addHandler(ch)

# silence Werkzeug access logs (verbose GET/POST lines)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

from docker_manager import (
    ServerManager,
    get_logs,
    get_install_progress,
    get_save_directory,
    list_save_files,
    load_server_config,
    save_uploaded_file,
    save_server_config,
    load_server_settings,
    save_server_settings,
    build_server_settings_fields,
    update_server_settings_from_form,
    clear_logs,
    clear_installation,
    clear_install_progress,
    set_install_error,
    log_error,
)

APP_VERSION = "1.0.0"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "frontend" / "templates"),
    static_folder=str(BASE_DIR / "frontend" / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

server_manager = ServerManager()
logger = logging.getLogger("fsm.app")


@app.route("/")
def home():
    config = load_server_config()
    server_settings = load_server_settings()
    return render_template(
        "index.html",
        status=server_manager.get_status(),
        logs=get_logs(),
        config=config,
        server_settings_fields=build_server_settings_fields(server_settings),
        save_files=list_save_files(),
        install_status=(
            "installing" if get_install_progress().get("status") == "progress" else server_manager.get_install_status()
        ),
        app_version=APP_VERSION,
    )


@app.route("/status")
def status():
    return jsonify(
        {
            "status": server_manager.get_status(),
            "install_status": "installing"
            if get_install_progress().get("status") == "progress"
            else server_manager.get_install_status(),
        }
    )


@app.route("/control/<action>", methods=["POST"])
def control(action: str):
    try:
        logger.info("control action requested: %s", action)
        if action == "start":
            server_manager.start_server()
        elif action == "stop":
            server_manager.stop_server()
        elif action == "restart":
            server_manager.restart_server()
    except Exception as exc:
        logger.exception("Action %s failed", action)
        log_error(f"Action {action} failed: {exc}")
    return redirect("/")


@app.route("/install", methods=["POST"])
def install():
    archive_path = request.form.get("archive_path", "").strip() or None
    try:
        server_manager.install_server(archive_path=archive_path)
    except Exception as exc:
        log_error(f"Install failed: {exc}")
    return redirect("/")


@app.route("/install/start", methods=["POST"])
def install_start():
    archive_path = request.form.get("archive_path", "").strip() or None
    progress = get_install_progress()
    if progress.get("status") == "progress":
        return jsonify({"error": "Installation already running."}), 409

    clear_install_progress()

    def run_install():
        try:
            logger.info("Starting server installation (archive: %s)", archive_path)
            server_manager.install_server(archive_path=archive_path)
            logger.info("Server installation finished")
        except Exception as exc:
            logger.exception("Install failed")
            set_install_error(str(exc))
            log_error(f"Install failed: {exc}")

    thread = threading.Thread(target=run_install, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/install/progress")
def install_progress():
    return jsonify(get_install_progress())


@app.route("/server-settings")
def server_settings_api():
    try:
        settings = load_server_settings()
        fields = build_server_settings_fields(settings)
        # Add small file metadata to help debug empty/missing settings issues
        try:
            settings_path = (Path(__file__).resolve().parent.parent / "factorio" / "config" / "server-settings.json")
            file_exists = settings_path.exists()
            file_size = settings_path.stat().st_size if file_exists else 0
            raw_preview = settings_path.read_text(encoding="utf-8", errors="replace")[:512] if file_exists else ""
        except Exception:
            file_exists = False
            file_size = 0
            raw_preview = ""

        logger.info("/server-settings requested: fields=%d keys=%d file_exists=%s size=%d", len(fields), len(settings.keys() if isinstance(settings, dict) else []), file_exists, file_size)
        return jsonify({"settings": settings, "fields": fields, "file_info": {"exists": file_exists, "size": file_size, "preview": raw_preview}})
    except Exception as exc:
        log_error(f"Failed to load server settings: {exc}")
        return jsonify({"settings": {}, "fields": []}), 500


@app.route("/config", methods=["POST"])
def update_config():
    config = load_server_config()
    server_name = request.form.get("server_name", "").strip() or config["server_name"]
    server_password = request.form.get("server_password", "").strip() or config["server_password"]
    save_server_config(values={"server_name": server_name, "server_password": server_password})

    current_settings = load_server_settings()
    updated_settings = update_server_settings_from_form(request.form, current_settings)
    save_server_settings(updated_settings)

    return redirect("/")


@app.route("/upload-save", methods=["POST"])
def upload_save():
    uploaded_file = request.files.get("save_file")
    if uploaded_file and uploaded_file.filename:
        try:
            save_uploaded_file(uploaded_file)
        except Exception as exc:
            log_error(f"Save upload failed: {exc}")
    return redirect("/")


@app.route("/logs/data")
def logs_data():
    return jsonify({"logs": get_logs()})


@app.route("/logs/clear", methods=["POST"])
def clear_log_route():
    try:
        clear_logs()
    except Exception as exc:
        log_error(f"Clear logs failed: {exc}")
    return redirect("/")


@app.route("/install/clear", methods=["POST"])
def clear_installation_route():
    try:
        clear_installation()
    except Exception as exc:
        log_error(f"Clear installation failed: {exc}")
    return redirect("/")


@app.route("/download-save/<path:filename>")
def download_save(filename: str):
    return send_from_directory(get_save_directory(), filename, as_attachment=True)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)