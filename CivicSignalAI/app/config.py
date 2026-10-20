import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_database_path() -> Path:
    configured_path = os.getenv("CIVICSIGNAL_DATABASE_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return PROJECT_ROOT / "data" / "civicsignal.db"
