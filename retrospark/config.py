import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".retrospark"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_BRAIN_DIR = CONFIG_DIR / "brain"

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get_brain_dir() -> Path:
    config = load_config()
    brain_dir = config.get("brain_dir")
    if brain_dir:
        return Path(brain_dir)
    return DEFAULT_BRAIN_DIR
