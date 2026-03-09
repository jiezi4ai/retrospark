import yaml
from pathlib import Path

# Standard: project-root config.yaml
PROJECT_ROOT = Path.cwd()
ROOT_CONFIG_FILE = PROJECT_ROOT / "config.yaml"

# Default interaction directory (local to project or custom)
DEFAULT_INTERACTION_DIR = PROJECT_ROOT / ".retrospark" / "interaction"

def load_config() -> dict:
    """Load configuration from the project-root config.yaml."""
    if ROOT_CONFIG_FILE.exists():
        try:
            with open(ROOT_CONFIG_FILE, "r") as f:
                config = yaml.safe_load(f)
                return config if isinstance(config, dict) else {}
        except (yaml.YAMLError, OSError):
            pass
    return {}

def save_config(config: dict) -> None:
    """Save configuration to the project-root config.yaml."""
    with open(ROOT_CONFIG_FILE, "w") as f:
        yaml.safe_dump(config, f, indent=2, sort_keys=False)

def get_interaction_dir() -> Path:
    """Returns the hardcoded interaction directory: ./.retrospark/interaction"""
    return DEFAULT_INTERACTION_DIR
