import sys
import logging
from pathlib import Path

from flask import Flask

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger.addHandler(ch)

logging.getLogger("werkzeug").setLevel(logging.WARNING)

from backend.routes.server_routes import register_server_routes
from backend.routes.save_routes import register_save_routes
from backend.routes.api_routes import register_api_routes

APP_VERSION = "2.0.0"


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend" / "templates"),
        static_folder=str(BASE_DIR / "frontend" / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    register_server_routes(app)
    register_save_routes(app)
    register_api_routes(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
