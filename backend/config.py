from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "backend" / "server_config.json"
INSTALL_DIR = BASE_DIR / "factorio"
SERVER_SETTINGS_DIR = BASE_DIR / "factorio" / "config"
SERVER_SETTINGS_PATH = SERVER_SETTINGS_DIR / "server-settings.json"
SERVER_SETTINGS_EXAMPLE_PATH = BASE_DIR / "backend" / "data" / "server-settings.example.json"
ADMINLIST_PATH = SERVER_SETTINGS_DIR / "server-adminlist.json"
WHITELIST_PATH = SERVER_SETTINGS_DIR / "server-whitelist.json"
BANLIST_PATH = SERVER_SETTINGS_DIR / "server-banlist.json"
SAVE_DIR = BASE_DIR / "data" / "saves"
ACTIVE_SAVE_PATH = BASE_DIR / "data" / "config" / "active_save.json"
LOG_DIR = BASE_DIR / "logs"
PID_PATH = BASE_DIR / "backend" / "server.pid"
INSTALL_PROGRESS_PATH = LOG_DIR / "install_progress.json"
INSTALL_LOG_NAME = "install.log"
SERVER_LOG_NAME = "server.log"
CRASH_LOG_NAME = "crash.log"
RUNTIME_LOG_NAME = "runtime.log"
INSTALL_LOG_PATH = LOG_DIR / INSTALL_LOG_NAME
SERVER_LOG_PATH = LOG_DIR / SERVER_LOG_NAME
CRASH_LOG_PATH = LOG_DIR / CRASH_LOG_NAME
RUNTIME_LOG_PATH = LOG_DIR / RUNTIME_LOG_NAME
MODS_DIR = BASE_DIR / "data" / "mods"
BACKUPS_DIR = BASE_DIR / "data" / "backups"
APP_SETTINGS_PATH = BASE_DIR / "data" / "settings.json"
PLAYER_DATA_PATH = BASE_DIR / "factorio" / "player-data.json"

DEFAULT_CONFIG: dict[str, str] = {
    "server_name": "factorio",
    "server_password": "change-me",
}

DEFAULT_APP_SETTINGS: dict[str, str] = {
    "language": "en",
    "rcon_host": "127.0.0.1",
    "rcon_port": "27015",
    "rcon_password": "",
    "rcon_timeout": "5",
    "server_port": "",
    "bind": "",
    "rcon_bind": "",
    "server_id": "",
    "use_authserver_bans": "false",
    "factorio_username": "",
    "factorio_service_token": "",
}

DEFAULT_INSTALL_ARCHIVE = os.getenv("FACTORIO_SERVER_ARCHIVE", "")
DEFAULT_INSTALL_URL = os.getenv(
    "FACTORIO_SERVER_ARCHIVE_URL",
    "https://factorio.com/get-download/stable/headless/linux64",
)
