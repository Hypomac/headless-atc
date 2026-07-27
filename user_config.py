from pathlib import Path
import json

CONFIG_DIR = Path.home() / ".config" / "headless-atc"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "controller_name": "",
}


def load_config():
    """Load user configuration or create defaults."""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        config = DEFAULT_CONFIG.copy()

    # Sørg for at nye nøklar blir lagt til ved framtidige oppdateringar
    for key, value in DEFAULT_CONFIG.items():
        config.setdefault(key, value)

    return config


def save_config(config):
    """Save user configuration."""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def get_controller_name():
    return load_config()["controller_name"]


def set_controller_name(name):
    config = load_config()
    config["controller_name"] = name.strip()
    save_config(config)
