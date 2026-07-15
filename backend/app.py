import threading
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory

try:
    from docker_manager import (
        ServerManager,
        get_logs,
        get_install_progress,
        get_save_directory,
        list_save_files,
        load_server_config,
        save_uploaded_file,
        save_server_config,
        clear_logs,
        clear_installation,
        clear_install_progress,
        set_install_error,
        log_error,
    )
except ImportError:  # pragma: no cover - allows importing as a package in tests
    from backend.docker_manager import (
        ServerManager,
        get_logs,
        get_install_progress,
        get_save_directory,
        list_save_files,
        load_server_config,
        save_uploaded_file,
        save_server_config,
        clear_logs,
        clear_installation,
        clear_install_progress,
        set_install_error,
        log_error,
    )

BASE_DIR = Path(__file__).resolve().parent.parent
APP_VERSION = "1.0.0"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "frontend" / "templates"),
    static_folder=str(BASE_DIR / "frontend" / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

server_manager = ServerManager()


@app.route("/")
def home():
    config = load_server_config()
    return render_template(
        "index.html",
        status=server_manager.get_status(),
        logs=get_logs(),
        config=config,
        save_files=list_save_files(),
        install_status=(
            "installing" if get_install_progress().get("status") == "progress" else server_manager.get_install_status()
        ),
        app_version=APP_VERSION,
    )


@app.route("/control/<action>", methods=["POST"])
def control(action: str):
    try:
        if action == "start":
            server_manager.start_server()
        elif action == "stop":
            server_manager.stop_server()
        elif action == "restart":
            server_manager.restart_server()
    except Exception as exc:
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
            server_manager.install_server(archive_path=archive_path)
        except Exception as exc:
            set_install_error(str(exc))
            log_error(f"Install failed: {exc}")

    thread = threading.Thread(target=run_install, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/install/progress")
def install_progress():
    return jsonify(get_install_progress())


@app.route("/config", methods=["POST"])
def update_config():
    config = load_server_config()
    server_name = request.form.get("server_name", "").strip() or config["server_name"]
    server_password = request.form.get("server_password", "").strip() or config["server_password"]
    save_server_config(values={"server_name": server_name, "server_password": server_password})
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