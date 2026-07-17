from __future__ import annotations

import logging
from pathlib import Path

from backend.services.save_service import (
    create_save,
    delete_save,
    get_active_save,
    get_save_directory,
    list_save_files,
    load_active_save,
    rename_save,
    save_uploaded_file,
    select_save,
)
from backend.services.factorio_service import log_error
from flask import Blueprint, redirect, request, send_from_directory

logger = logging.getLogger("fsm.routes.save")

save_bp = Blueprint("save", __name__)


@save_bp.route("/upload-save", methods=["POST"])
def upload_save():
    uploaded_file = request.files.get("save_file")
    if uploaded_file and uploaded_file.filename:
        try:
            save_uploaded_file(uploaded_file)
        except Exception as exc:
            log_error(f"Save upload failed: {exc}")
    return redirect("/")


@save_bp.route("/download-save/<path:filename>")
def download_save(filename: str):
    return send_from_directory(get_save_directory(), filename, as_attachment=True)


@save_bp.route("/api/saves", methods=["GET"])
def api_saves_list():
    files = []
    for filename in list_save_files():
        path = get_save_directory() / filename
        active = get_active_save()
        files.append({
            "name": filename,
            "size": path.stat().st_size if path.exists() else 0,
            "modified": int(path.stat().st_mtime) if path.exists() else 0,
            "active": active == filename,
        })
    return {"saves": files}


@save_bp.route("/api/saves/create", methods=["POST"])
def api_saves_create():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    seed = data.get("seed", "").strip() or None

    if not name:
        return {"error": "name is required"}, 400

    try:
        result = create_save(name, seed)
        return result
    except FileExistsError as exc:
        return {"error": str(exc)}, 409
    except Exception as exc:
        logger.exception("Create save failed")
        return {"error": str(exc)}, 500


@save_bp.route("/api/saves/select", methods=["POST"])
def api_saves_select():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "").strip()

    if not filename:
        return {"error": "filename is required"}, 400

    try:
        result = select_save(filename)
        return result
    except FileNotFoundError as exc:
        return {"error": str(exc)}, 404
    except Exception as exc:
        logger.exception("Select save failed")
        return {"error": str(exc)}, 500


@save_bp.route("/api/saves/<path:filename>", methods=["DELETE"])
def api_saves_delete(filename: str):
    try:
        result = delete_save(filename)
        return result
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except FileNotFoundError as exc:
        return {"error": str(exc)}, 404
    except Exception as exc:
        logger.exception("Delete save failed")
        return {"error": str(exc)}, 500


@save_bp.route("/api/saves/rename", methods=["POST"])
def api_saves_rename():
    data = request.get_json(silent=True) or {}
    old_name = data.get("old_name", "").strip()
    new_name = data.get("new_name", "").strip()

    if not old_name or not new_name:
        return {"error": "old_name and new_name are required"}, 400

    try:
        result = rename_save(old_name, new_name)
        return result
    except (FileNotFoundError, FileExistsError) as exc:
        return {"error": str(exc)}, 404
    except Exception as exc:
        logger.exception("Rename save failed")
        return {"error": str(exc)}, 500


def register_save_routes(app):
    app.register_blueprint(save_bp)
