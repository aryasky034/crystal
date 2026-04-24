# ============================================================
#  CRYSTAL AI - Helpers
#  Shared utility functions used across all modules
# ============================================================

import os
import json
from datetime import datetime


def timestamp() -> str:
    """Returns current time as a readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path: str):
    """Creates a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def read_json(path: str, default=None):
    """
    Safely reads a JSON file.
    Returns default if file is missing or empty.
    """
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except (json.JSONDecodeError, IOError):
        return default


def write_json(path: str, data):
    """Safely writes data to a JSON file."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clear_screen():
    """Clears the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamps a value between min and max."""
    return max(min_val, min(max_val, value))