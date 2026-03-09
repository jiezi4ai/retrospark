import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

class SkillManifest:
    def __init__(self, data: Dict[str, Any], path: Path):
        self.name = data.get("name")
        self.description = data.get("description")
        self.api_base_url = data.get("api_base_url")
        self.required_secrets = data.get("required_secrets", [])
        self.github_repo = data.get("github_repo", [])
        self.antigravity = data.get("antigravity", [])
        self.path = path

    @property
    def remote_url(self) -> Optional[str]:
        if isinstance(self.github_repo, dict):
            return self.github_repo.get("remote_url")
        if self.github_repo and isinstance(self.github_repo, list) and len(self.github_repo) > 0:
            return self.github_repo[0].get("remote_url")
        return None

    @property
    def history_path(self) -> Optional[str]:
        if isinstance(self.antigravity, dict):
            return self.antigravity.get("history_path")
        if self.antigravity and isinstance(self.antigravity, list) and len(self.antigravity) > 0:
            return self.antigravity[0].get("history_path")
        return None

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "SkillManifest":
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(data, yaml_path.parent)

class SkillManager:
    def __init__(self, skills_root: Path):
        self.skills_root = skills_root

    def load_manifest(self, skill_name: str) -> Optional[SkillManifest]:
        manifest_path = self.skills_root / skill_name / "manifest.yaml"
        if not manifest_path.exists():
            return None
        return SkillManifest.from_yaml(manifest_path)

    def load_config(self, config_path: Path) -> Optional[SkillManifest]:
        """Load a manifest from an arbitrary config file path."""
        if not config_path.exists():
            return None
        try:
            return SkillManifest.from_yaml(config_path)
        except Exception:
            return None

    def list_skills(self) -> List[str]:
        if not self.skills_root.exists():
            return []
        return [d.name for d in self.skills_root.iterdir() if d.is_dir()]
