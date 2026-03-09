import json
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors.common import _make_stats, _make_session_result, _normalize_timestamp, _update_time_bounds, _safe_int
from retrospark.extractors.tools import _parse_tool_input

OPENCLAW_SOURCE = "openclaw"
OPENCLAW_DIR = Path.home() / ".openclaw"
OPENCLAW_AGENTS_DIR = OPENCLAW_DIR / "agents"
UNKNOWN_OPENCLAW_CWD = "<unknown-cwd>"

def discover_projects() -> list[dict]:
    index = _build_openclaw_project_index()
    projects = []
    for cwd, session_files in sorted(index.items()):
        if not session_files:
            continue
        total_size = sum(f.stat().st_size for f in session_files if f.exists())
        projects.append(
            {
                "dir_name": cwd,
                "display_name": _build_openclaw_project_name(cwd),
                "session_count": len(session_files),
                "total_size_bytes": total_size,
                "source": OPENCLAW_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    index = _build_openclaw_project_index()
    session_files = index.get(project_dir_name, [])
    sessions = []
    for session_file in session_files:
        parsed = _parse_openclaw_session_file(session_file, anonymizer, include_thinking)
        if parsed and parsed["messages"]:
            parsed["project"] = _build_openclaw_project_name(project_dir_name)
            parsed["source"] = OPENCLAW_SOURCE
            sessions.append(parsed)
    return sessions

def _build_openclaw_project_index() -> dict[str, list[Path]]:
    if not OPENCLAW_AGENTS_DIR.exists():
        return {}
    index = {}
    try:
        for agent_dir in sorted(OPENCLAW_AGENTS_DIR.iterdir()):
            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.is_dir():
                continue
            for session_file in sorted(sessions_dir.glob("*.jsonl")):
                cwd = _extract_openclaw_cwd(session_file) or UNKNOWN_OPENCLAW_CWD
                index.setdefault(cwd, []).append(session_file)
    except OSError:
        pass
    return index

def _extract_openclaw_cwd(session_file: Path) -> str | None:
    try:
        with open(session_file) as f:
            first_line = f.readline().strip()
            if not first_line:
                return None
            header = json.loads(first_line)
            if header.get("type") != "session":
                return None
            cwd = header.get("cwd")
            if isinstance(cwd, str) and cwd.strip():
                return cwd
    except (json.JSONDecodeError, OSError):
        pass
    return None

def _build_openclaw_project_name(cwd: str) -> str:
    if cwd == UNKNOWN_OPENCLAW_CWD:
        return "openclaw:unknown"
    return f"openclaw:{Path(cwd).name or cwd}"

def _parse_openclaw_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool = True) -> dict | None:
    def _iter_jsonl(p):
        with open(p) as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    try:
        entries = list(_iter_jsonl(filepath))
    except OSError:
        return None

    if not entries:
        return None

    header = entries[0]
    if header.get("type") != "session":
        return None

    metadata = {
        "session_id": header.get("id", filepath.stem),
        "cwd": None,
        "git_branch": None,
        "model": None,
        "start_time": header.get("timestamp"),
        "end_time": None,
    }
    cwd = header.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        metadata["cwd"] = anonymizer.path(cwd)

    messages = []
    stats = _make_stats()

    tool_result_map = {}
    for entry in entries[1:]:
        if entry.get("type") != "message":
            continue
        msg_data = entry.get("message", {})
        if msg_data.get("role") != "toolResult":
            continue
        tool_call_id = msg_data.get("toolCallId")
        if not tool_call_id:
            continue
        is_error = bool(msg_data.get("isError"))
        content = msg_data.get("content", [])
        if isinstance(content, list):
            text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            output_text = "\n".join(text_parts).strip()
        elif isinstance(content, str):
            output_text = content.strip()
        else:
            output_text = ""
        tool_result_map[tool_call_id] = {
            "output": {"text": anonymizer.text(output_text)} if output_text else {},
            "status": "error" if is_error else "success",
        }

    for entry in entries[1:]:
        entry_type = entry.get("type")
        timestamp = entry.get("timestamp")

        if entry_type == "model_change":
            provider = entry.get("provider", "")
            model_id = entry.get("modelId", "")
            if model_id:
                metadata["model"] = f"{provider}/{model_id}" if provider else model_id

        if entry_type != "message":
            continue

        msg_data = entry.get("message", {})
        role = msg_data.get("role")
        msg_ts = msg_data.get("timestamp")
        if isinstance(msg_ts, (int, float)):
            msg_ts = _normalize_timestamp(msg_ts)
        effective_ts = msg_ts or timestamp

        if role == "user":
            content = msg_data.get("content")
            if isinstance(content, list):
                text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                text = "\n".join(text_parts)
            elif isinstance(content, str):
                text = content
            else:
                continue
            if not text.strip():
                continue
            messages.append({"role": "user", "content": anonymizer.text(text.strip()), "timestamp": effective_ts})
            stats["user_messages"] += 1
            _update_time_bounds(metadata, effective_ts)

        elif role == "assistant":
            model = msg_data.get("model")
            if model and metadata["model"] is None:
                provider = msg_data.get("provider", "")
                metadata["model"] = f"{provider}/{model}" if provider else model

            usage = msg_data.get("usage", {})
            if isinstance(usage, dict):
                stats["input_tokens"] += _safe_int(usage.get("input")) + _safe_int(usage.get("cacheRead"))
                stats["output_tokens"] += _safe_int(usage.get("output"))

            content = msg_data.get("content", [])
            if not isinstance(content, list):
                continue

            text_parts, thinking_parts, tool_uses = [], [], []
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type == "text":
                    text = block.get("text", "")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(anonymizer.text(text.strip()))
                elif block_type == "thinking" and include_thinking:
                    thinking = block.get("thinking", "")
                    if isinstance(thinking, str) and thinking.strip():
                        thinking_parts.append(anonymizer.text(thinking.strip()))
                elif block_type == "toolCall":
                    tool_name = block.get("name")
                    args = block.get("arguments", {})
                    tool_entry = {"tool": tool_name, "input": _parse_tool_input(tool_name, args, anonymizer)}
                    tool_call_id = block.get("id")
                    if tool_call_id and tool_call_id in tool_result_map:
                        result = tool_result_map[tool_call_id]
                        if result.get("output"): tool_entry["output"] = result["output"]
                        if result.get("status"): tool_entry["status"] = result["status"]
                    tool_uses.append(tool_entry)

            if not text_parts and not thinking_parts and not tool_uses:
                continue

            msg = {"role": "assistant"}
            if effective_ts: msg["timestamp"] = effective_ts
            if text_parts: msg["content"] = "\n\n".join(text_parts)
            if thinking_parts: msg["thinking"] = "\n\n".join(thinking_parts)
            if tool_uses:
                msg["tool_uses"] = tool_uses
                stats["tool_uses"] += len(tool_uses)

            messages.append(msg)
            stats["assistant_messages"] += 1
            _update_time_bounds(metadata, effective_ts)

        elif role == "bashExecution":
            command = msg_data.get("command", "")
            output = msg_data.get("output", "")
            exit_code = msg_data.get("exitCode")
            is_error = exit_code is not None and exit_code != 0
            tool_entry = {"tool": "bash", "input": {"command": anonymizer.text(command)} if command else {}}
            out_dict = {}
            if output: out_dict["text"] = anonymizer.text(output.strip())
            if exit_code is not None: out_dict["exit_code"] = exit_code
            if out_dict: tool_entry["output"] = out_dict
            tool_entry["status"] = "error" if is_error else "success"
            messages.append({"role": "assistant", "tool_uses": [tool_entry], "timestamp": effective_ts})
            stats["assistant_messages"] += 1
            stats["tool_uses"] += 1
            _update_time_bounds(metadata, effective_ts)

    if metadata["model"] is None:
        metadata["model"] = "openclaw-unknown"

    return _make_session_result(metadata, messages, stats)
