# ============================================================
#  CRYSTAL AI - Config Loader
#  Reads config/config.yaml and provides it to all modules
# ============================================================

import yaml
import os

_config = None

def load_config(path: str = None) -> dict:
    global _config

    if _config is not None:
        return _config

    if path is None:
        # Always resolve relative to project root (where main.py lives)
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "config", "config.yaml")

    with open(path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)

    return _config


def get(section: str, key: str = None, default=None):
    """
    Quick access helper.
    Usage:
        get("brain", "model")        → "qwen2:1.5b"
        get("brain")                 → full brain dict
    """
    cfg = load_config()
    section_data = cfg.get(section, {})

    if key is None:
        return section_data

    return section_data.get(key, default)