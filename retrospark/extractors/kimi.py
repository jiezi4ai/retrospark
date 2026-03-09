import json
import hashlib
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors.common import _make_stats, _make_session_result
from retrospark.extractors.tools import _parse_tool_input

KIMI_SOURCE = "kimi"
KIMI_DIR = Path.home() / ".kimi"
KIMI_SESSIONS_DIR = KIMI_DIR / "sessions"
KIMI_CONFIG_PATH = KIMI_DIR / "kimi.json"
UNKNOWN_KIMI_CWD = "<unknown-cwd>"

def _iter_jsonl(filepath: Path):
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: yield json.loads(line)
            except json.JSONDecodeError: continue

def _load_kimi_work_dirs() -> dict[str, str]:
    if not KIMI_CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(KIMI_CONFIG_PATH.read_text())
        work_dirs = data.get("work_dirs", [])
        return {entry.get("path", ""): entry.get("path", "") for entry in work_dirs if entry.get("path")}
    except (json.JSONDecodeError, OSError):
        return {}

def _get_kimi_project_hash(cwd: str) -> str:
    return hashlib.md5(cwd.encode()).hexdigest()

def _build_kimi_project_name(cwd: str) -> str:
    if cwd == UNKNOWN_KIMI_CWD:
        return "kimi:unknown"
    return f"kimi:{Path(cwd).name or cwd}"

def discover_projects() -> list[dict]:
    if not KIMI_SESSIONS_DIR.exists():
        return []

    work_dirs = _load_kimi_work_dirs()
    path_to_hash = {path: _get_kimi_project_hash(path) for path in work_dirs}
    hash_to_path = {h: p for p, h in path_to_hash.items()}

    projects = []
    for project_dir in sorted(KIMI_SESSIONS_DIR.iterdir()):
        if not project_dir.is_dir(): continue

        project_hash = project_dir.name
        session_dirs = [d for d in project_dir.iterdir() if d.is_dir()]
        if not session_dirs: continue

        total_sessions, total_size = 0, 0
        for session_dir in session_dirs:
            context_file = session_dir / "context.jsonl"
            if context_file.exists():
                total_sessions += 1
                total_size += context_file.stat().st_size

        if total_sessions == 0: continue

        project_path = hash_to_path.get(project_hash)
        if project_path:
            display_name = f"kimi:{Path(project_path).name}"
            dir_name = project_path
        else:
            display_name = f"kimi:{project_hash[:8]}"
            dir_name = project_hash

        projects.append(
            {
                "dir_name": dir_name,
                "display_name": display_name,
                "session_count": total_sessions,
                "total_size_bytes": total_size,
                "source": KIMI_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    project_hash = _get_kimi_project_hash(project_dir_name)
    project_path = KIMI_SESSIONS_DIR / project_hash
    if not project_path.exists():
        return []
    sessions = []
    for session_dir in sorted(project_path.iterdir()):
        if not session_dir.is_dir(): continue
        context_file = session_dir / "context.jsonl"
        if not context_file.exists(): continue
        parsed = _parse_kimi_session_file(context_file, anonymizer=anonymizer, include_thinking=include_thinking)
        if parsed and parsed["messages"]:
            parsed["project"] = _build_kimi_project_name(project_dir_name)
            parsed["source"] = KIMI_SOURCE
            if not parsed.get("model"): parsed["model"] = "kimi-k2"
            sessions.append(parsed)
    return sessions

def _parse_kimi_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool = True) -> dict | None:
    messages = []
    metadata = {
        "session_id": filepath.parent.name,
        "cwd": None,
        "git_branch": None,
        "model": None,
        "start_time": None,
        "end_time": None,
    }
    stats = _make_stats()

    try:
        for entry in _iter_jsonl(filepath):
            role = entry.get("role")
            if role == "user":
                content = entry.get("content")
                if isinstance(content, str) and content.strip():
                    messages.append({"role": "user", "content": anonymizer.text(content.strip()), "timestamp": None})
                    stats["user_messages"] += 1
            elif role == "assistant":
                msg = {"role": "assistant"}
                content = entry.get("content")
                text_parts, thinking_parts = [], []
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict): continue
                        block_type = block.get("type")
                        if block_type == "text":
                            text = block.get("text", "").strip()
                            if text: text_parts.append(anonymizer.text(text))
                        elif block_type == "think" and include_thinking:
                            think = block.get("think", "").strip()
                            if think: thinking_parts.append(anonymizer.text(think))
                if text_parts: msg["content"] = "\n\n".join(text_parts)
                if thinking_parts: msg["thinking"] = "\n\n".join(thinking_parts)
                tool_calls = entry.get("tool_calls", [])
                tool_uses = []
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if not isinstance(tc, dict): continue
                        func = tc.get("function", {})
                        if isinstance(func, dict):
                            tool_name = func.get("name")
                            args_str = func.get("arguments", "")
                            try: args = json.loads(args_str) if isinstance(args_str, str) else args_str
                            except json.JSONDecodeError: args = args_str
                            tool_uses.append({"tool": tool_name, "input": _parse_tool_input(tool_name, args, anonymizer)})
                if tool_uses:
                    msg["tool_uses"] = tool_uses
                    stats["tool_uses"] += len(tool_uses)
                if text_parts or thinking_parts or tool_uses:
                    messages.append(msg)
                    stats["assistant_messages"] += 1
            elif role == "_usage":
                token_count = entry.get("token_count")
                if isinstance(token_count, int):
                    stats["output_tokens"] = max(stats["output_tokens"], token_count)
    except OSError: return None
    return _make_session_result(metadata, messages, stats)
