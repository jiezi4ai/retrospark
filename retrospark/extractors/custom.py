import json
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.privacy.secrets import redact_text

CUSTOM_SOURCE = "custom"
CUSTOM_DIR = Path.home() / ".dataclaw" / "custom"

def _iter_jsonl(filepath: Path):
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: yield json.loads(line)
            except json.JSONDecodeError: continue

def discover_projects() -> list[dict]:
    if not CUSTOM_DIR.exists():
        return []
    projects = []
    for project_dir in sorted(CUSTOM_DIR.iterdir()):
        if not project_dir.is_dir(): continue
        jsonl_files = list(project_dir.glob("*.jsonl"))
        if not jsonl_files: continue
        session_count, total_size = 0, 0
        for f in jsonl_files:
            total_size += f.stat().st_size
            try: session_count += sum(1 for line in f.open() if line.strip())
            except OSError: pass
        if session_count == 0: continue
        projects.append(
            {
                "dir_name": project_dir.name,
                "display_name": f"custom:{project_dir.name}",
                "session_count": session_count,
                "total_size_bytes": total_size,
                "source": CUSTOM_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer) -> list[dict]:
    project_path = CUSTOM_DIR / project_dir_name
    if not project_path.exists():
        return []
    required_fields = {"session_id", "model", "messages"}
    sessions = []
    for jsonl_file in sorted(project_path.glob("*.jsonl")):
        try:
            for line_num, line in enumerate(jsonl_file.open(), 1):
                line = line.strip()
                if not line: continue
                try: session = json.loads(line)
                except json.JSONDecodeError: continue
                if not isinstance(session, dict): continue
                missing = required_fields - session.keys()
                if missing: continue
                session["project"] = f"custom:{project_dir_name}"
                session["source"] = CUSTOM_SOURCE
                for msg in session.get("messages", []):
                    if "content" in msg and isinstance(msg["content"], str):
                        redacted, _ = redact_text(msg["content"])
                        msg["content"] = anonymizer.text(redacted)
                sessions.append(session)
        except OSError: pass
    return sessions
