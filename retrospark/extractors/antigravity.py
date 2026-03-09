import json
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.privacy.secrets import redact_text
from retrospark.extractors.common import _make_stats

ANTIGRAVITY_SOURCE = "antigravity"
ANTIGRAVITY_DIR = Path.home() / ".gemini" / "antigravity" / "brain"

def _iter_jsonl(filepath: Path):
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: yield json.loads(line)
            except json.JSONDecodeError: continue

def discover_projects() -> list[dict]:
    if not ANTIGRAVITY_DIR.exists():
        return []
    projects = []
    for project_dir in sorted(ANTIGRAVITY_DIR.iterdir()):
        if not project_dir.is_dir(): continue
        logs_dir = project_dir / ".system_generated" / "logs"
        if not logs_dir.exists(): continue
        jsonl_files = list(logs_dir.glob("*.jsonl"))
        if not jsonl_files: continue
        total_size = sum(f.stat().st_size for f in jsonl_files)
        projects.append(
            {
                "dir_name": project_dir.name,
                "display_name": f"antigravity:{project_dir.name[:8]}",
                "session_count": len(jsonl_files),
                "total_size_bytes": total_size,
                "source": ANTIGRAVITY_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    project_path = ANTIGRAVITY_DIR / project_dir_name / ".system_generated" / "logs"
    if not project_path.exists():
        return []
    sessions = []
    for session_file in sorted(project_path.glob("*.jsonl")):
        parsed = _parse_antigravity_session_file(session_file, anonymizer, include_thinking)
        if parsed and parsed["messages"]:
            parsed["project"] = f"antigravity:{project_dir_name[:8]}"
            parsed["source"] = ANTIGRAVITY_SOURCE
            sessions.append(parsed)
    return sessions

def _parse_antigravity_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool) -> dict | None:
    session_id = filepath.stem
    messages = []
    metadata = {
        "session_id": session_id,
        "cwd": None,
        "git_branch": None,
        "model": "gemini-2.5-pro", # Default for antigravity
        "start_time": None,
        "end_time": None,
    }
    stats = _make_stats()
    for data in _iter_jsonl(filepath):
        if "role" not in data: continue
        role = data["role"]
        if metadata["start_time"] is None and "timestamp" in data:
            metadata["start_time"] = data["timestamp"]
        if "timestamp" in data:
            metadata["end_time"] = data["timestamp"]
        content_str = ""
        if isinstance(data.get("content"), str):
            content_str = data["content"]
        elif isinstance(data.get("content"), list):
            content_str = " ".join([c.get("text", "") for c in data["content"] if isinstance(c, dict)])
        redacted, _ = redact_text(content_str)
        content_str = anonymizer.text(redacted)
        msg = {"role": role, "content": content_str, "timestamp": data.get("timestamp")}
        messages.append(msg)
        if role == "user": stats["user_messages"] += 1
        else: stats["assistant_messages"] += 1
    if not messages: return None
    return {"messages": messages, "stats": stats, **metadata}
