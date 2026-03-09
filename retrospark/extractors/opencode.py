import sqlite3
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors.common import _make_stats, _make_session_result, _normalize_timestamp, _update_time_bounds, _load_json_field, _safe_int

OPENCODE_SOURCE = "opencode"
OPENCODE_DIR = Path.home() / ".local" / "share" / "opencode"
OPENCODE_DB_PATH = OPENCODE_DIR / "opencode.db"
UNKNOWN_OPENCODE_CWD = "<unknown-cwd>"

def discover_projects() -> list[dict]:
    index = _build_opencode_project_index()
    total_sessions = sum(len(session_ids) for session_ids in index.values())
    db_size = OPENCODE_DB_PATH.stat().st_size if OPENCODE_DB_PATH.exists() else 0

    projects = []
    for cwd, session_ids in sorted(index.items()):
        if not session_ids:
            continue
        estimated_size = int(db_size * (len(session_ids) / total_sessions)) if total_sessions else 0
        projects.append(
            {
                "dir_name": cwd,
                "display_name": _build_opencode_project_name(cwd),
                "session_count": len(session_ids),
                "total_size_bytes": estimated_size,
                "source": OPENCODE_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    index = _build_opencode_project_index()
    session_ids = index.get(project_dir_name, [])
    sessions = []
    for session_id in session_ids:
        parsed = _parse_opencode_session(
            session_id,
            anonymizer=anonymizer,
            include_thinking=include_thinking,
            target_cwd=project_dir_name,
        )
        if parsed and parsed["messages"]:
            parsed["project"] = _build_opencode_project_name(project_dir_name)
            parsed["source"] = OPENCODE_SOURCE
            sessions.append(parsed)
    return sessions

def _build_opencode_project_index() -> dict[str, list[str]]:
    if not OPENCODE_DB_PATH.exists():
        return {}
    index = {}
    try:
        with sqlite3.connect(OPENCODE_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, directory FROM session ORDER BY time_updated DESC, id DESC"
            ).fetchall()
    except sqlite3.Error:
        return {}
    for session_id, cwd in rows:
        normalized_cwd = cwd if isinstance(cwd, str) and cwd.strip() else UNKNOWN_OPENCODE_CWD
        if not isinstance(session_id, str) or not session_id:
            continue
        index.setdefault(normalized_cwd, []).append(session_id)
    return index

def _build_opencode_project_name(cwd: str) -> str:
    if cwd == UNKNOWN_OPENCODE_CWD:
        return "opencode:unknown"
    return f"opencode:{Path(cwd).name or cwd}"

def _parse_opencode_session(session_id: str, anonymizer: Anonymizer, include_thinking: bool, target_cwd: str) -> dict | None:
    if not OPENCODE_DB_PATH.exists():
        return None
    messages = []
    metadata = {
        "session_id": session_id,
        "cwd": None,
        "git_branch": None,
        "model": None,
        "start_time": None,
        "end_time": None,
    }
    stats = _make_stats()
    try:
        with sqlite3.connect(OPENCODE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            session_row = conn.execute(
                "SELECT id, directory, time_created, time_updated FROM session WHERE id = ?",
                (session_id,),
            ).fetchone()
            if session_row is None:
                return None
            raw_cwd = session_row["directory"]
            if isinstance(raw_cwd, str) and raw_cwd.strip():
                if raw_cwd != target_cwd:
                    return None
                metadata["cwd"] = anonymizer.path(raw_cwd)
            elif target_cwd != UNKNOWN_OPENCODE_CWD:
                return None
            metadata["start_time"] = _normalize_timestamp(session_row["time_created"])
            metadata["end_time"] = _normalize_timestamp(session_row["time_updated"])
            message_rows = conn.execute(
                "SELECT id, data, time_created FROM message WHERE session_id = ? ORDER BY time_created ASC, id ASC",
                (session_id,),
            ).fetchall()
            for message_row in message_rows:
                message_data = _load_json_field(message_row["data"])
                role = message_data.get("role")
                timestamp = _normalize_timestamp(message_row["time_created"])
                model = _extract_opencode_model(message_data)
                if metadata["model"] is None and model:
                    metadata["model"] = model
                part_rows = conn.execute(
                    "SELECT data FROM part WHERE message_id = ? ORDER BY time_created ASC, id ASC",
                    (message_row["id"],),
                ).fetchall()
                parts = [_load_json_field(part_row["data"]) for part_row in part_rows]
                if role == "user":
                    content = _extract_opencode_user_content(parts, anonymizer)
                    if content is not None:
                        messages.append({"role": "user", "content": content, "timestamp": timestamp})
                        stats["user_messages"] += 1
                        _update_time_bounds(metadata, timestamp)
                elif role == "assistant":
                    msg = _extract_opencode_assistant_content(parts, anonymizer, include_thinking)
                    if msg:
                        msg["timestamp"] = timestamp
                        messages.append(msg)
                        stats["assistant_messages"] += 1
                        stats["tool_uses"] += len(msg.get("tool_uses", []))
                        _update_time_bounds(metadata, timestamp)
                    tokens = message_data.get("tokens", {})
                    if isinstance(tokens, dict):
                        cache = tokens.get("cache", {})
                        cache_read = _safe_int(cache.get("read")) if isinstance(cache, dict) else 0
                        cache_write = _safe_int(cache.get("write")) if isinstance(cache, dict) else 0
                        stats["input_tokens"] += _safe_int(tokens.get("input")) + cache_read + cache_write
                        stats["output_tokens"] += _safe_int(tokens.get("output"))
    except (sqlite3.Error, OSError):
        return None
    if metadata["model"] is None:
        metadata["model"] = "opencode-unknown"
    return _make_session_result(metadata, messages, stats)

def _extract_opencode_model(message_data: dict) -> str | None:
    model = message_data.get("model")
    if not isinstance(model, dict):
        return None
    provider_id = model.get("providerID")
    model_id = model.get("modelID")
    if isinstance(provider_id, str) and provider_id.strip() and isinstance(model_id, str) and model_id.strip():
        return f"{provider_id}/{model_id}"
    if isinstance(model_id, str) and model_id.strip():
        return model_id
    return None

def _extract_opencode_user_content(parts: list[dict], anonymizer: Anonymizer) -> str | None:
    text_parts = []
    for part in parts:
        if not isinstance(part, dict) or part.get("type") != "text":
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            text_parts.append(anonymizer.text(text.strip()))
    if not text_parts:
        return None
    return "\n\n".join(text_parts)

def _extract_opencode_assistant_content(parts: list[dict], anonymizer: Anonymizer, include_thinking: bool) -> dict | None:
    text_parts = []
    thinking_parts = []
    tool_uses = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        part_type = part.get("type")
        if part_type == "text":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(anonymizer.text(text.strip()))
        elif part_type == "reasoning" and include_thinking:
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                thinking_parts.append(anonymizer.text(text.strip()))
        elif part_type == "tool":
            tool_name = part.get("tool")
            state = part.get("state", {})
            tool_input = state.get("input", {}) if isinstance(state, dict) else {}
            tu = {
                "tool": tool_name,
                "input": tool_input, # Should use _parse_tool_input if shared
            }
            if isinstance(state, dict):
                status = state.get("status")
                if isinstance(status, str):
                    tu["status"] = "success" if status == "completed" else status
                output = state.get("output")
                if isinstance(output, str) and output:
                    tu["output"] = {"text": anonymizer.text(output)}
                elif output is not None:
                    tu["output"] = {}
            tool_uses.append(tu)
    if not text_parts and not thinking_parts and not tool_uses:
        return None
    msg = {"role": "assistant"}
    if text_parts:
        msg["content"] = "\n\n".join(text_parts)
    if thinking_parts:
        msg["thinking"] = "\n\n".join(thinking_parts)
    if tool_uses:
        msg["tool_uses"] = tool_uses
    return msg
