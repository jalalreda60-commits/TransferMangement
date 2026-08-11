"""
config.py
---------
Central configuration: app-wide constants, filesystem paths, and the
small JSON-based settings store (database location, theme, notification
window) that persists between runs.
"""
import json
import sys
from pathlib import Path

APP_NAME = "Transfer Management System"
APP_ORG = "IndustrialOps"
APP_VERSION = "1.0.0"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
ATTACHMENTS_DIR = DATA_DIR / "attachments"
EXPORTS_DIR = DATA_DIR / "exports"
SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_DB_PATH = DATA_DIR / "transfer_management.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "db_path": str(DEFAULT_DB_PATH),
    "theme": "light",
    "notify_days_before_due": 7,
}


def resource_path(*parts: str) -> Path:
    """Resolve a bundled read-only resource (icons, ...) so it works both
    running from source and as a frozen PyInstaller executable."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        root = Path(meipass) if meipass else BASE_DIR
    else:
        root = BASE_DIR
    return root.joinpath(*parts)


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get_db_path() -> str:
    settings = load_settings()
    path = settings.get("db_path") or str(DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


def set_db_path(new_path: str) -> None:
    settings = load_settings()
    settings["db_path"] = new_path
    save_settings(settings)
