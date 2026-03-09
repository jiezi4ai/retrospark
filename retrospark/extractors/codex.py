import json
import dataclasses
from pathlib import Path
from typing import Any
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors.common import _make_stats, _make_session_result, _normalize_timestamp, _update_time_bounds, _safe_int
from retrospark.extractors.tools import _parse_tool_input

CODEX_SOURCE = "codex"
CODEX_DIR = Path.home() / ".codex"
CODEX_SESSIONS_DIR = CODEX_DIR / "sessions"
CODEX_ARCHIVED_DIR = CODEX_DIR / "archived_sessions"
UNKNOWN_CODEX_CWD = "<unknown-cwd>"

@dataclasses.dataclass
class _CodexParseState:
    messages: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    stats: dict[str, int] = dataclasses.field(default_factory=_make_stats)
    pending_tool_uses: list[dict[str, str | None]] = dataclasses.field(default_factory=list)
    pending_thinking: list[str] = dataclasses.field(default_factory=list)
    _pending_thinking_seen: set[str] = dataclasses.field(default_factory=set)
    raw_cwd: str = UNKNOWN_CODEX_CWD
    max_input_tokens: int = 0
    max_output_tokens: int = 0
    tool_result_map: dict[str, dict] = dataclasses.field(default_factory=dict)

def _iter_jsonl(filepath: Path):
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
    index = _build_codex_project_index()
    projects = []
    for cwd, session_files in sorted(index.items()):
        if not session_files:
            continue
        projects.append(
            {
                "dir_name": cwd,
                "display_name": _build_codex_project_name(cwd),
                "session_count": len(session_files),
                "total_size_bytes": sum(f.stat().st_size for f in session_files),
                "source": CODEX_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    index = _build_codex_project_index()
    session_files = index.get(project_dir_name, [])
    sessions = []
    for session_file in session_files:
        parsed = _parse_codex_session_file(
            session_file,
            anonymizer=anonymizer,
            include_thinking=include_thinking,
            target_cwd=project_dir_name,
        )
        if parsed and parsed["messages"]:
            parsed["project"] = _build_codex_project_name(project_dir_name)
            parsed["source"] = CODEX_SOURCE
            sessions.append(parsed)
    return sessions

def _build_codex_project_index() -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for session_file in _iter_codex_session_files():
        cwd = _extract_codex_cwd(session_file) or UNKNOWN_CODEX_CWD
        index.setdefault(cwd, []).append(session_file)
    return index

def _iter_codex_session_files() -> list[Path]:
    files: list[Path] = []
    if CODEX_SESSIONS_DIR.exists():
        files.extend(sorted(CODEX_SESSIONS_DIR.rglob("*.jsonl")))
    if CODEX_ARCHIVED_DIR.exists():
        files.extend(sorted(CODEX_ARCHIVED_DIR.glob("*.jsonl")))
    return files

def _extract_codex_cwd(session_file: Path) -> str | None:
    try:
        for entry in _iter_jsonl(session_file):
            if entry.get("type") in ("session_meta", "turn_context"):
                cwd = entry.get("payload", {}).get("cwd")
                if isinstance(cwd, str) and cwd.strip():
                    return cwd
    except OSError:
        return None
    return None

def _build_codex_project_name(cwd: str) -> str:
    if cwd == UNKNOWN_CODEX_CWD:
        return "codex:unknown"
    return f"codex:{Path(cwd).name or cwd}"

def _parse_codex_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool, target_cwd: str) -> dict | None:
    state = _CodexParseState(
        metadata={
            "session_id": filepath.stem,
            "cwd": None,
            "git_branch": None,
            "model": None,
            "start_time": None,
            "end_time": None,
            "model_provider": None,
        },
    )

    try:
        entries = list(_iter_jsonl(filepath))
    except OSError:
        return None

    state.tool_result_map = _build_codex_tool_result_map(entries, anonymizer)

    for entry in entries:
        timestamp = _normalize_timestamp(entry.get("timestamp"))
        entry_type = entry.get("type")

        if entry_type == "session_meta":
            _handle_codex_session_meta(state, entry, filepath, anonymizer)
        elif entry_type == "turn_context":
            _handle_codex_turn_context(state, entry, anonymizer)
        elif entry_type == "response_item":
            _handle_codex_response_item(state, entry, anonymizer, include_thinking)
        elif entry_type == "event_msg":
            payload = entry.get("payload", {})
            event_type = payload.get("type")
            if event_type == "token_count":
                _handle_codex_token_count(state, payload)
            elif event_type == "agent_reasoning" and include_thinking:
                thinking = payload.get("text")
                if isinstance(thinking, str) and thinking.strip():
                    cleaned = anonymizer.text(thinking.strip())
                    if cleaned not in state._pending_thinking_seen:
                        state._pending_thinking_seen.add(cleaned)
                        state.pending_thinking.append(cleaned)
            elif event_type == "user_message":
                _handle_codex_user_message(state, payload, timestamp, anonymizer)
            elif event_type == "agent_message":
                _handle_codex_agent_message(state, payload, timestamp, anonymizer, include_thinking)

    state.stats["input_tokens"] = state.max_input_tokens
    state.stats["output_tokens"] = state.max_output_tokens

    if state.raw_cwd != target_cwd:
        return None

    _flush_codex_pending(state, timestamp=state.metadata["end_time"])

    if state.metadata["model"] is None:
        model_provider = state.metadata.get("model_provider")
        if isinstance(model_provider, str) and model_provider.strip():
            state.metadata["model"] = f"{model_provider}-codex"
        else:
            state.metadata["model"] = "codex-unknown"

    return _make_session_result(state.metadata, state.messages, state.stats)

def _build_codex_tool_result_map(entries: list[dict], anonymizer: Anonymizer) -> dict:
    result = {}
    for entry in entries:
        if entry.get("type") != "response_item":
            continue
        p = entry.get("payload", {})
        pt = p.get("type")
        call_id = p.get("call_id")
        if not call_id:
            continue

        if pt == "function_call_output":
            raw = p.get("output", "")
            out = {}
            lines = raw.splitlines()
            output_lines = []
            in_output = False
            for line in lines:
                if line.startswith("Exit code: "):
                    try:
                        out["exit_code"] = int(line[len("Exit code: "):].strip())
                    except ValueError:
                        out["exit_code"] = line[len("Exit code: "):].strip()
                elif line.startswith("Wall time: "):
                    out["wall_time"] = line[len("Wall time: "):].strip()
                elif line == "Output:":
                    in_output = True
                elif in_output:
                    output_lines.append(line)
            if output_lines:
                out["output"] = anonymizer.text("\n".join(output_lines).strip())
            result[call_id] = {"output": out, "status": "success"}

        elif pt == "custom_tool_call_output":
            raw = p.get("output", "")
            out = {}
            try:
                parsed = json.loads(raw)
                text = parsed.get("output", "")
                if text:
                    out["output"] = anonymizer.text(str(text))
                meta = parsed.get("metadata", {})
                if "exit_code" in meta:
                    out["exit_code"] = meta["exit_code"]
                if "duration_seconds" in meta:
                    out["duration_seconds"] = meta["duration_seconds"]
            except (json.JSONDecodeError, AttributeError):
                if raw:
                    out["output"] = anonymizer.text(raw)
            result[call_id] = {"output": out, "status": "success"}

    return result

def _handle_codex_session_meta(state: _CodexParseState, entry: dict, filepath: Path, anonymizer: Anonymizer):
    payload = entry.get("payload", {})
    session_cwd = payload.get("cwd")
    if isinstance(session_cwd, str) and session_cwd.strip():
        state.raw_cwd = session_cwd
        if state.metadata["cwd"] is None:
            state.metadata["cwd"] = anonymizer.path(session_cwd)
    if state.metadata["session_id"] == filepath.stem:
        state.metadata["session_id"] = payload.get("id", state.metadata["session_id"])
    if state.metadata["model_provider"] is None:
        state.metadata["model_provider"] = payload.get("model_provider")
    git_info = payload.get("git", {})
    if isinstance(git_info, dict) and state.metadata["git_branch"] is None:
        state.metadata["git_branch"] = git_info.get("branch")

def _handle_codex_turn_context(state: _CodexParseState, entry: dict, anonymizer: Anonymizer):
    payload = entry.get("payload", {})
    session_cwd = payload.get("cwd")
    if isinstance(session_cwd, str) and session_cwd.strip():
        state.raw_cwd = session_cwd
        if state.metadata["cwd"] is None:
            state.metadata["cwd"] = anonymizer.path(session_cwd)
    if state.metadata["model"] is None:
        model_name = payload.get("model")
        if isinstance(model_name, str) and model_name.strip():
            state.metadata["model"] = model_name

def _handle_codex_response_item(state: _CodexParseState, entry: dict, anonymizer: Anonymizer, include_thinking: bool):
    payload = entry.get("payload", {})
    item_type = payload.get("type")
    if item_type == "function_call":
        tool_name = payload.get("name")
        args_data = _parse_codex_tool_arguments(payload.get("arguments"))
        state.pending_tool_uses.append(
            {
                "tool": tool_name,
                "input": _parse_tool_input(tool_name, args_data, anonymizer),
                "_call_id": payload.get("call_id"),
            }
        )
    elif item_type == "custom_tool_call":
        tool_name = payload.get("name")
        raw_input = payload.get("input", "")
        inp = {"patch": anonymizer.text(raw_input)} if isinstance(raw_input, str) else _parse_tool_input(tool_name, raw_input, anonymizer)
        state.pending_tool_uses.append(
            {
                "tool": tool_name,
                "input": inp,
                "_call_id": payload.get("call_id"),
            }
        )
    elif item_type == "reasoning" and include_thinking:
        for summary in payload.get("summary", []):
            if not isinstance(summary, dict):
                continue
            text = summary.get("text")
            if isinstance(text, str) and text.strip():
                cleaned = anonymizer.text(text.strip())
                if cleaned not in state._pending_thinking_seen:
                    state._pending_thinking_seen.add(cleaned)
                    state.pending_thinking.append(cleaned)

def _handle_codex_token_count(state: _CodexParseState, payload: dict):
    info = payload.get("info", {})
    if isinstance(info, dict):
        total_usage = info.get("total_token_usage", {})
        if isinstance(total_usage, dict):
            input_tokens = _safe_int(total_usage.get("input_tokens"))
            cached_tokens = _safe_int(total_usage.get("cached_input_tokens"))
            output_tokens = _safe_int(total_usage.get("output_tokens"))
            state.max_input_tokens = max(state.max_input_tokens, input_tokens + cached_tokens)
            state.max_output_tokens = max(state.max_output_tokens, output_tokens)

def _handle_codex_user_message(state: _CodexParseState, payload: dict, timestamp: str | None, anonymizer: Anonymizer):
    _flush_codex_pending(state, timestamp)
    content = payload.get("message")
    if isinstance(content, str) and content.strip():
        state.messages.append(
            {
                "role": "user",
                "content": anonymizer.text(content.strip()),
                "timestamp": timestamp,
            }
        )
        state.stats["user_messages"] += 1
        _update_time_bounds(state.metadata, timestamp)

def _resolve_codex_tool_uses(state: _CodexParseState) -> list[dict]:
    resolved = []
    for tu in state.pending_tool_uses:
        call_id = tu.pop("_call_id", None)
        if call_id and call_id in state.tool_result_map:
            r = state.tool_result_map[call_id]
            tu["output"] = r["output"]
            tu["status"] = r["status"]
        resolved.append(tu)
    return resolved

def _handle_codex_agent_message(state: _CodexParseState, payload: dict, timestamp: str | None, anonymizer: Anonymizer, include_thinking: bool):
    content = payload.get("message")
    msg = {"role": "assistant"}
    if isinstance(content, str) and content.strip():
        msg["content"] = anonymizer.text(content.strip())
    if state.pending_thinking and include_thinking:
        msg["thinking"] = "\n\n".join(state.pending_thinking)
    if state.pending_tool_uses:
        msg["tool_uses"] = _resolve_codex_tool_uses(state)

    if len(msg) > 1:
        msg["timestamp"] = timestamp
        state.messages.append(msg)
        state.stats["assistant_messages"] += 1
        state.stats["tool_uses"] += len(msg.get("tool_uses", []))
        _update_time_bounds(state.metadata, timestamp)

    state.pending_tool_uses.clear()
    state.pending_thinking.clear()
    state._pending_thinking_seen.clear()

def _flush_codex_pending(state: _CodexParseState, timestamp: str | None):
    if not state.pending_tool_uses and not state.pending_thinking:
        return

    msg = {"role": "assistant", "timestamp": timestamp}
    if state.pending_thinking:
        msg["thinking"] = "\n\n".join(state.pending_thinking)
    if state.pending_tool_uses:
        msg["tool_uses"] = _resolve_codex_tool_uses(state)

    state.messages.append(msg)
    state.stats["assistant_messages"] += 1
    state.stats["tool_uses"] += len(msg.get("tool_uses", []))
    _update_time_bounds(state.metadata, timestamp)

    state.pending_tool_uses.clear()
    state.pending_thinking.clear()
    state._pending_thinking_seen.clear()

def _parse_codex_tool_arguments(arguments: Any) -> Any:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
        return parsed
    return arguments
