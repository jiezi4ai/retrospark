import json
import os
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.privacy.secrets import redact_text
from retrospark.extractors.common import _make_stats, _make_session_result
from retrospark.skills.manager import SkillManager

ANTIGRAVITY_SOURCE = "antigravity"
ANTIGRAVITY_DIR = Path.home() / ".gemini" / "antigravity" / "brain"

# Hardcoded export directory for Antigravity (relative to project root)
EXPORT_DIR = Path.cwd() / "artifacts"

def get_export_dir() -> Path:
    """Returns the hardcoded export directory."""
    return EXPORT_DIR

def _iter_jsonl(filepath: Path):
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: yield json.loads(line)
            except json.JSONDecodeError: continue

def discover_projects() -> list[dict]:
    projects_map = {}

    # 1. Discover from brain directory (Artifacts)
    if ANTIGRAVITY_DIR.exists():
        for project_dir in sorted(ANTIGRAVITY_DIR.iterdir()):
            if not project_dir.is_dir(): continue
            
            # Even without logs, we consider it a project if brain data exists
            logs_dir = project_dir / ".system_generated" / "logs"
            has_logs = logs_dir.exists() and any(logs_dir.glob("*.jsonl"))
            
            projects_map[project_dir.name] = {
                "dir_name": project_dir.name,
                "display_name": f"antigravity:{project_dir.name[:8]}",
                "session_count": 0,
                "total_size_bytes": 0,
                "source": ANTIGRAVITY_SOURCE,
            }
            if has_logs:
                jsonl_files = list(logs_dir.glob("*.jsonl"))
                projects_map[project_dir.name]["session_count"] = int(len(jsonl_files))
                projects_map[project_dir.name]["total_size_bytes"] = int(sum(f.stat().st_size for f in jsonl_files))

    # 2. Discover from export directory (Bypass sessions)
    if EXPORT_DIR.exists():
        for export_file in EXPORT_DIR.glob("chat_history_*.json"):
            try:
                with open(export_file) as f:
                    data = json.load(f)
                session_id = data.get("session_id")
                if not session_id or not isinstance(session_id, str): continue
                
                if session_id not in projects_map:
                    projects_map[session_id] = {
                        "dir_name": session_id,
                        "display_name": f"antigravity:{session_id[:8]}",
                        "session_count": 0,
                        "total_size_bytes": 0,
                        "source": ANTIGRAVITY_SOURCE,
                    }
                projects_map[session_id]["session_count"] += 1
                projects_map[session_id]["total_size_bytes"] += int(export_file.stat().st_size)
            except (json.JSONDecodeError, OSError):
                continue

    return sorted(projects_map.values(), key=lambda p: p["dir_name"])

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    sessions = []
    session_ids_processed = set()

    # 1. Try to load from export JSON (Preferred for full chat history)
    if EXPORT_DIR.exists():
        pattern = f"chat_history_{project_dir_name}.json"
        for export_file in EXPORT_DIR.glob(pattern):
            parsed = _parse_antigravity_export_json(export_file, anonymizer, include_thinking)
            if parsed:
                parsed["project"] = f"antigravity:{project_dir_name[:8]}"
                parsed["source"] = ANTIGRAVITY_SOURCE
                sessions.append(parsed)
                session_ids_processed.add(project_dir_name)
    
    # 2. Fallback or complement with brain logs
    project_path = ANTIGRAVITY_DIR / project_dir_name / ".system_generated" / "logs"
    if project_path.exists():
        for session_file in sorted(project_path.glob("*.jsonl")):
            if session_file.stem in session_ids_processed: continue
            
            parsed = _parse_antigravity_session_file(session_file, anonymizer, include_thinking)
            if parsed and parsed["messages"]:
                parsed["project"] = f"antigravity:{project_dir_name[:8]}"
                parsed["source"] = ANTIGRAVITY_SOURCE
                sessions.append(parsed)
    
    # If no messages found but brain exists, return a metadata-only session (minimal)
    if not sessions and (ANTIGRAVITY_DIR / project_dir_name).exists():
        # RetroSpark logic usually expects messages, so we might skip or return empty
        pass

    return sessions

def _parse_antigravity_export_json(filepath: Path, anonymizer: Anonymizer, include_thinking: bool) -> dict | None:
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    messages = []
    stats = _make_stats()
    
    for msg in data.get("messages", []):
        role = msg.get("role")
        content = msg.get("content", "")
        
        # Anonymize
        redacted, _ = redact_text(content)
        content = anonymizer.text(redacted)
        
        new_msg = {
            "role": role,
            "content": content,
            "timestamp": msg.get("timestamp")
        }
        
        if include_thinking and "thinking" in msg:
            thought_redacted, _ = redact_text(msg["thinking"])
            new_msg["thinking"] = anonymizer.text(thought_redacted)
            
        if "tool_uses" in msg:
            new_msg["tool_uses"] = msg["tool_uses"] # Assuming they are already structured
            stats["tool_uses"] += len(msg["tool_uses"])
            
        messages.append(new_msg)
        if role == "user": stats["user_messages"] += 1
        else: stats["assistant_messages"] += 1

    metadata = {
        "session_id": data.get("session_id", filepath.stem.replace("chat_history_", "")),
        "cwd": None,
        "git_branch": None,
        "model": data.get("model", "gemini-2.5-pro"),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
    }
    
    # In practice, brain artifacts are handled later by the transformer, 
    # but we provide the base session here.
    return _make_session_result(metadata, messages, stats)

def _parse_antigravity_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool) -> dict | None:
    session_id = filepath.stem
    messages = []
    metadata = {
        "session_id": session_id,
        "cwd": None,
        "git_branch": None,
        "model": "gemini-2.5-pro",
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
