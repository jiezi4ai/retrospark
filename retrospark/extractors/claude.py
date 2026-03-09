import json
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors.common import _make_stats, _make_session_result, _normalize_timestamp, _update_time_bounds
from retrospark.extractors.tools import _parse_tool_input

CLAUDE_SOURCE = "claude"
CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"

def _iter_jsonl(filepath: Path):
    """Yield parsed JSON objects from a JSONL file, skipping blank/malformed lines."""
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def discover_projects() -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []

    projects = []
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        root_sessions = list(project_dir.glob("*.jsonl"))
        subagent_sessions = _find_subagent_only_sessions(project_dir)
        total_count = len(root_sessions) + len(subagent_sessions)
        if total_count == 0:
            continue
        total_size = sum(f.stat().st_size for f in root_sessions)
        for session_dir in subagent_sessions:
            for sa_file in (session_dir / "subagents").glob("agent-*.jsonl"):
                total_size += sa_file.stat().st_size
        projects.append(
            {
                "dir_name": project_dir.name,
                "display_name": _build_project_name(project_dir.name),
                "session_count": total_count,
                "total_size_bytes": total_size,
                "source": CLAUDE_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    project_path = PROJECTS_DIR / project_dir_name
    if not project_path.exists():
        return []

    sessions = []
    for session_file in sorted(project_path.glob("*.jsonl")):
        parsed = _parse_claude_session_file(session_file, anonymizer, include_thinking)
        if parsed and parsed["messages"]:
            parsed["project"] = _build_project_name(project_dir_name)
            parsed["source"] = CLAUDE_SOURCE
            sessions.append(parsed)

    for session_dir in _find_subagent_only_sessions(project_path):
        parsed = _parse_subagent_session(session_dir, anonymizer, include_thinking)
        if parsed and parsed["messages"]:
            parsed["project"] = _build_project_name(project_dir_name)
            parsed["source"] = CLAUDE_SOURCE
            sessions.append(parsed)

    return sessions

def _build_project_name(dir_name: str) -> str:
    path = dir_name.replace("-", "/")
    path = path.lstrip("/")
    parts = path.split("/")
    common_dirs = {"Documents", "Downloads", "Desktop"}

    if len(parts) >= 2 and parts[0] == "Users":
        if len(parts) >= 4 and parts[2] in common_dirs:
            meaningful = parts[3:]
        elif len(parts) >= 3 and parts[2] not in common_dirs:
            meaningful = parts[2:]
        else:
            meaningful = []
    elif len(parts) >= 2 and parts[0] == "home":
        meaningful = parts[2:] if len(parts) > 2 else []
    else:
        meaningful = parts

    if meaningful:
        segments = dir_name.lstrip("-").split("-")
        prefix_parts = len(parts) - len(meaningful)
        return "-".join(segments[prefix_parts:]) or dir_name
    else:
        if len(parts) >= 2 and parts[0] in ("Users", "home"):
            if len(parts) == 2:
                return "~home"
            if len(parts) == 3 and parts[2] in common_dirs:
                return f"~{parts[2]}"
        return dir_name.strip("-") or "unknown"

def _find_subagent_only_sessions(project_dir: Path) -> list[Path]:
    root_stems = {f.stem for f in project_dir.glob("*.jsonl")}
    sessions = []
    for entry in sorted(project_dir.iterdir()):
        if not entry.is_dir() or entry.name in root_stems:
            continue
        subagent_dir = entry / "subagents"
        if subagent_dir.is_dir() and any(subagent_dir.glob("agent-*.jsonl")):
            sessions.append(entry)
    return sessions

def _parse_claude_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool = True) -> dict | None:
    messages = []
    metadata = {
        "session_id": filepath.stem,
        "cwd": None,
        "git_branch": None,
        "claude_version": None,
        "model": None,
        "start_time": None,
        "end_time": None,
    }
    stats = _make_stats()

    try:
        entries = list(_iter_jsonl(filepath))
    except OSError:
        return None

    tool_result_map = _build_tool_result_map(entries, anonymizer)
    for entry in entries:
        _process_entry(entry, messages, metadata, stats, anonymizer, include_thinking, tool_result_map)

    return _make_session_result(metadata, messages, stats)

def _parse_subagent_session(session_dir: Path, anonymizer: Anonymizer, include_thinking: bool = True) -> dict | None:
    subagent_dir = session_dir / "subagents"
    if not subagent_dir.is_dir():
        return None

    timed_entries = []
    for sa_file in sorted(subagent_dir.glob("agent-*.jsonl")):
        for entry in _iter_jsonl(sa_file):
            ts = entry.get("timestamp", "")
            timed_entries.append((ts if isinstance(ts, str) else "", entry))

    if not timed_entries:
        return None

    timed_entries.sort(key=lambda pair: pair[0])

    messages = []
    metadata = {
        "session_id": session_dir.name,
        "cwd": None,
        "git_branch": None,
        "claude_version": None,
        "model": None,
        "start_time": None,
        "end_time": None,
    }
    stats = _make_stats()

    entries = [entry for _ts, entry in timed_entries]
    tool_result_map = _build_tool_result_map(entries, anonymizer)
    for entry in entries:
        _process_entry(entry, messages, metadata, stats, anonymizer, include_thinking, tool_result_map)

    return _make_session_result(metadata, messages, stats)

def _build_tool_result_map(entries: list[dict], anonymizer: Anonymizer) -> dict:
    result = {}
    for entry in entries:
        if entry.get("type") != "user":
            continue
        for block in entry.get("message", {}).get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tid = block.get("tool_use_id")
            if not tid:
                continue
            is_error = bool(block.get("is_error"))
            content = block.get("content", "")
            if isinstance(content, list):
                text = "\n\n".join(
                    part.get("text", "") for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ).strip()
            else:
                text = str(content).strip() if content else ""
            result[tid] = {
                "output": {"text": anonymizer.text(text)} if text else {},
                "status": "error" if is_error else "success",
            }
    return result

def _process_entry(entry: dict, messages: list, metadata: dict, stats: dict, anonymizer: Anonymizer, include_thinking: bool, tool_result_map: dict = None):
    entry_type = entry.get("type")

    if metadata["cwd"] is None and entry.get("cwd"):
        metadata["cwd"] = anonymizer.path(entry["cwd"])
        metadata["git_branch"] = entry.get("gitBranch")
        metadata["claude_version"] = entry.get("version")
        metadata["session_id"] = entry.get("sessionId", metadata["session_id"])

    timestamp = _normalize_timestamp(entry.get("timestamp"))

    if entry_type == "user":
        content = _extract_user_content(entry, anonymizer)
        if content is not None:
            messages.append({"role": "user", "content": content, "timestamp": timestamp})
            stats["user_messages"] += 1
            _update_time_bounds(metadata, timestamp)

    elif entry_type == "assistant":
        msg = _extract_assistant_content(entry, anonymizer, include_thinking, tool_result_map)
        if msg:
            if metadata["model"] is None:
                metadata["model"] = entry.get("message", {}).get("model")
            usage = entry.get("message", {}).get("usage", {})
            stats["input_tokens"] += usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
            stats["output_tokens"] += usage.get("output_tokens", 0)
            stats["tool_uses"] += len(msg.get("tool_uses", []))
            msg["timestamp"] = timestamp
            messages.append(msg)
            stats["assistant_messages"] += 1
            _update_time_bounds(metadata, timestamp)

def _extract_user_content(entry: dict, anonymizer: Anonymizer) -> str | None:
    msg_data = entry.get("message", {})
    content = msg_data.get("content", "")
    if isinstance(content, list):
        text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
        content = "\n".join(text_parts)
    if not content or not content.strip():
        return None
    return anonymizer.text(content)

def _extract_assistant_content(entry: dict, anonymizer: Anonymizer, include_thinking: bool, tool_result_map: dict = None) -> dict | None:
    msg_data = entry.get("message", {})
    content_blocks = msg_data.get("content", [])
    if not isinstance(content_blocks, list):
        return None

    text_parts = []
    thinking_parts = []
    tool_uses = []

    for block in content_blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text", "").strip()
            if text:
                text_parts.append(anonymizer.text(text))
        elif block_type == "thinking" and include_thinking:
            thinking = block.get("thinking", "").strip()
            if thinking:
                thinking_parts.append(anonymizer.text(thinking))
        elif block_type == "tool_use":
            tu = {
                "tool": block.get("name"),
                "input": _parse_tool_input(block.get("name"), block.get("input", {}), anonymizer),
            }
            if tool_result_map is not None:
                result = tool_result_map.get(block.get("id", ""))
                if result:
                    tu["output"] = result["output"]
                    tu["status"] = result["status"]
            tool_uses.append(tu)

    if not text_parts and not tool_uses and not thinking_parts:
        return None

    msg = {"role": "assistant"}
    if text_parts:
        msg["content"] = "\n\n".join(text_parts)
    if thinking_parts:
        msg["thinking"] = "\n\n".join(thinking_parts)
    if tool_uses:
        msg["tool_uses"] = tool_uses
    return msg
