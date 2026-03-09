import yaml
from pathlib import Path

# Standard: project-root config.yaml
PROJECT_ROOT = Path.cwd()
ROOT_CONFIG_FILE = PROJECT_ROOT / "config.yaml"

# Default brain directory (local to project or custom)
DEFAULT_BRAIN_DIR = PROJECT_ROOT / ".retrospark" / "brain"

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

def get_brain_dir() -> Path:
    """Get the brain directory, checking config and providing a default."""
    config = load_config()
    brain_dir = config.get("brain_dir")
    if brain_dir:
        return Path(brain_dir).resolve()
    return DEFAULT_BRAIN_DIR
