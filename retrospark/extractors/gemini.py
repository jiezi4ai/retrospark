import json
import hashlib
from pathlib import Path
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.extractors.common import _make_stats, _make_session_result, _update_time_bounds

GEMINI_SOURCE = "gemini"
GEMINI_DIR = Path.home() / ".gemini" / "tmp"
_GEMINI_HASH_MAP: dict[str, str] = {}

def _build_gemini_hash_map() -> dict[str, str]:
    result: dict[str, str] = {}
    home = Path.home()
    try:
        for entry in home.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                h = hashlib.sha256(str(entry).encode()).hexdigest()
                result[h] = str(entry)
    except OSError:
        pass
    return result

def _extract_project_path_from_sessions(project_hash: str) -> str | None:
    chats_dir = GEMINI_DIR / project_hash / "chats"
    if not chats_dir.exists():
        return None
    for session_file in sorted(chats_dir.glob("session-*.json"), reverse=True):
        try:
            data = json.loads(session_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for msg in data.get("messages", []):
            for tc in msg.get("toolCalls", []):
                fp = tc.get("args", {}).get("file_path") or tc.get("args", {}).get("path", "")
                if fp.startswith("/"):
                    parts = Path(fp).parts
                    for depth in range(3, len(parts)):
                        candidate = str(Path(*parts[:depth + 1]))
                        if hashlib.sha256(candidate.encode()).hexdigest() == project_hash:
                            return candidate
        break
    return None

def _resolve_gemini_hash(project_hash: str) -> str:
    global _GEMINI_HASH_MAP
    if not _GEMINI_HASH_MAP:
        _GEMINI_HASH_MAP = _build_gemini_hash_map()
    full_path = _GEMINI_HASH_MAP.get(project_hash)
    if full_path:
        return Path(full_path).name
    extracted = _extract_project_path_from_sessions(project_hash)
    if extracted:
        _GEMINI_HASH_MAP[project_hash] = extracted
        return Path(extracted).name
    return project_hash[:8]

def discover_projects() -> list[dict]:
    if not GEMINI_DIR.exists():
        return []

    projects = []
    for project_dir in sorted(GEMINI_DIR.iterdir()):
        if not project_dir.is_dir() or project_dir.name == "bin":
            continue
        chats_dir = project_dir / "chats"
        if not chats_dir.exists():
            continue
        sessions = list(chats_dir.glob("session-*.json"))
        if not sessions:
            continue
        projects.append(
            {
                "dir_name": project_dir.name,
                "display_name": f"gemini:{_resolve_gemini_hash(project_dir.name)}",
                "session_count": len(sessions),
                "total_size_bytes": sum(f.stat().st_size for f in sessions),
                "source": GEMINI_SOURCE,
            }
        )
    return projects

def parse_project_sessions(project_dir_name: str, anonymizer: Anonymizer, include_thinking: bool = True) -> list[dict]:
    project_path = GEMINI_DIR / project_dir_name / "chats"
    if not project_path.exists():
        return []
    sessions = []
    for session_file in sorted(project_path.glob("session-*.json")):
        parsed = _parse_gemini_session_file(session_file, anonymizer, include_thinking)
        if parsed and parsed["messages"]:
            parsed["project"] = f"gemini:{_resolve_gemini_hash(project_dir_name)}"
            parsed["source"] = GEMINI_SOURCE
            sessions.append(parsed)
    return sessions

def _parse_gemini_tool_call(tc: dict, anonymizer: Anonymizer) -> dict:
    name = tc.get("name")
    args = tc.get("args", {})
    status = tc.get("status", "unknown")
    result_list = tc.get("result") or []

    output_text = None
    extra_texts = []
    for item in result_list:
        if not isinstance(item, dict):
            continue
        if "functionResponse" in item:
            resp = item["functionResponse"].get("response", {})
            output_text = resp.get("output")
        elif "text" in item:
            extra_texts.append(item["text"])

    if name == "read_file":
        inp = {"file_path": anonymizer.path(args.get("file_path", ""))}
    elif name == "write_file":
        inp = {
            "file_path": anonymizer.path(args.get("file_path", "")),
            "content": anonymizer.text(args.get("content", "")),
        }
    elif name == "replace":
        inp = {
            "file_path": anonymizer.path(args.get("file_path", "")),
            "old_string": anonymizer.text(args.get("old_string", "")),
            "new_string": anonymizer.text(args.get("new_string", "")),
            "expected_replacements": args.get("expected_replacements"),
            "instruction": anonymizer.text(args.get("instruction", "")) if args.get("instruction") else None,
        }
        inp = {k: v for k, v in inp.items() if v is not None}
    elif name == "run_shell_command":
        inp = {"command": anonymizer.text(args.get("command", ""))}
    elif name == "read_many_files":
        inp = {"paths": [anonymizer.path(p) for p in args.get("paths", [])]}
    elif name in ("search_file_content", "grep_search"):
        inp = {k: anonymizer.text(str(v)) for k, v in args.items()}
    elif name == "list_directory":
        inp = {"dir_path": anonymizer.path(args.get("dir_path", ""))}
        if args.get("ignore"):
            inp["ignore"] = [anonymizer.text(str(p)) for p in args["ignore"]] if isinstance(args["ignore"], list) else anonymizer.text(str(args["ignore"]))
    elif name == "glob":
        inp = {"pattern": args.get("pattern", "")}
    elif name in ("google_web_search", "web_fetch", "codebase_investigator"):
        inp = {k: anonymizer.text(str(v)) for k, v in args.items()}
    else:
        inp = {k: anonymizer.text(str(v)) if isinstance(v, str) else v for k, v in args.items()}

    if name == "read_many_files":
        files = []
        for raw in extra_texts:
            lines = raw.split("\n")
            current_path = None
            content_lines = []
            for line in lines:
                if line.startswith("--- ") and line.endswith(" ---"):
                    if current_path is not None:
                        files.append({
                            "path": anonymizer.path(current_path),
                            "content": anonymizer.text("\n".join(content_lines).strip()),
                        })
                    current_path = line[4:-4].strip()
                    content_lines = []
                else:
                    content_lines.append(line)
            if current_path is not None:
                files.append({
                    "path": anonymizer.path(current_path),
                    "content": anonymizer.text("\n".join(content_lines).strip()),
                })
        out = {"files": files}
    elif name == "run_shell_command" and output_text:
        parsed = {}
        current_key = None
        current_val = []
        for line in output_text.splitlines():
            for key, prefix in (("command", "Command: "), ("directory", "Directory: "),
                                 ("output", "Output: "), ("exit_code", "Exit Code: ")):
                if line.startswith(prefix):
                    if current_key:
                        parsed[current_key] = "\n".join(current_val).strip()
                    current_key = key
                    current_val = [line[len(prefix):]]
                    break
            else:
                if current_key:
                    current_val.append(line)
        if current_key:
            parsed[current_key] = "\n".join(current_val).strip()
        if "exit_code" in parsed:
            try:
                parsed["exit_code"] = int(parsed["exit_code"])
            except ValueError:
                pass
        if "command" in parsed:
            parsed["command"] = anonymizer.text(parsed["command"])
        if "directory" in parsed:
            parsed["directory"] = anonymizer.path(parsed["directory"])
        if "output" in parsed:
            parsed["output"] = anonymizer.text(parsed["output"])
        out = parsed
    elif output_text is not None:
        out = {"text": anonymizer.text(output_text)}
    else:
        out = {}

    result = {"tool": name, "input": inp, "output": out, "status": status}
    return result

def _parse_gemini_session_file(filepath: Path, anonymizer: Anonymizer, include_thinking: bool = True) -> dict | None:
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    messages = []
    metadata = {
        "session_id": data.get("sessionId", filepath.stem),
        "cwd": None,
        "git_branch": None,
        "model": None,
        "start_time": data.get("startTime"),
        "end_time": data.get("lastUpdated"),
    }
    stats = _make_stats()

    for msg_data in data.get("messages", []):
        msg_type = msg_data.get("type")
        timestamp = msg_data.get("timestamp")

        if msg_type == "user":
            content = msg_data.get("content")
            if isinstance(content, list):
                text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and "text" in part]
                text = "\n".join(text_parts)
            elif isinstance(content, str):
                text = content
            else:
                continue
            if not text.strip():
                continue
            messages.append({
                "role": "user",
                "content": anonymizer.text(text.strip()),
                "timestamp": timestamp,
            })
            stats["user_messages"] += 1
            _update_time_bounds(metadata, timestamp)

        elif msg_type == "gemini":
            if metadata["model"] is None:
                metadata["model"] = msg_data.get("model")

            tokens = msg_data.get("tokens", {})
            if tokens:
                stats["input_tokens"] += tokens.get("input", 0) + tokens.get("cached", 0)
                stats["output_tokens"] += tokens.get("output", 0)

            msg = {"role": "assistant"}
            if timestamp:
                msg["timestamp"] = timestamp

            content = msg_data.get("content")
            if isinstance(content, str) and content.strip():
                msg["content"] = anonymizer.text(content.strip())

            if include_thinking:
                thoughts = msg_data.get("thoughts", [])
                if thoughts:
                    thought_texts = []
                    for t in thoughts:
                        if "description" in t and isinstance(t["description"], str):
                            thought_texts.append(t["description"].strip())
                    if thought_texts:
                        msg["thinking"] = anonymizer.text("\n\n".join(thought_texts))

            tool_uses = []
            for tc in msg_data.get("toolCalls", []):
                tool_uses.append(_parse_gemini_tool_call(tc, anonymizer))

            if tool_uses:
                msg["tool_uses"] = tool_uses
                stats["tool_uses"] += len(tool_uses)

            if "content" in msg or "thinking" in msg or "tool_uses" in msg:
                messages.append(msg)
                stats["assistant_messages"] += 1
                _update_time_bounds(metadata, timestamp)

    return _make_session_result(metadata, messages, stats)
