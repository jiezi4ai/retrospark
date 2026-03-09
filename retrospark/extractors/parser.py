"""Central dispatcher for discovering and parsing session data from various AI assistants."""

import logging
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors import (
    claude,
    codex,
    gemini,
    opencode,
    openclaw,
    kimi,
    custom,
    antigravity,
)

logger = logging.getLogger(__name__)

# Re-exporting source constants for CLI compatibility
CLAUDE_SOURCE = claude.CLAUDE_SOURCE
CODEX_SOURCE = codex.CODEX_SOURCE
GEMINI_SOURCE = gemini.GEMINI_SOURCE
OPENCODE_SOURCE = opencode.OPENCODE_SOURCE
OPENCLAW_SOURCE = openclaw.OPENCLAW_SOURCE
KIMI_SOURCE = kimi.KIMI_SOURCE
CUSTOM_SOURCE = custom.CUSTOM_SOURCE
ANTIGRAVITY_SOURCE = antigravity.ANTIGRAVITY_SOURCE

def discover_projects() -> list[dict]:
    """Discover all supported source projects with session counts."""
    projects = []
    projects.extend(claude.discover_projects())
    projects.extend(codex.discover_projects())
    projects.extend(gemini.discover_projects())
    projects.extend(opencode.discover_projects())
    projects.extend(openclaw.discover_projects())
    projects.extend(kimi.discover_projects())
    projects.extend(custom.discover_projects())
    projects.extend(antigravity.discover_projects())
    return sorted(projects, key=lambda p: (p["display_name"], p["source"]))

def parse_project_sessions(
    project_dir_name: str,
    anonymizer: Anonymizer,
    include_thinking: bool = True,
    source: str = CLAUDE_SOURCE,
) -> list[dict]:
    """Parse all sessions for a project using the appropriate source extractor."""
    if source == CLAUDE_SOURCE:
        return claude.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    elif source == CODEX_SOURCE:
        return codex.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    elif source == GEMINI_SOURCE:
        return gemini.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    elif source == OPENCODE_SOURCE:
        return opencode.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    elif source == OPENCLAW_SOURCE:
        return openclaw.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    elif source == KIMI_SOURCE:
        return kimi.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    elif source == CUSTOM_SOURCE:
        return custom.parse_project_sessions(project_dir_name, anonymizer)
    elif source == ANTIGRAVITY_SOURCE:
        return antigravity.parse_project_sessions(project_dir_name, anonymizer, include_thinking)
    else:
        logger.error(f"Unsupported source: {source}")
        return []
