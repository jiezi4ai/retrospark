from pathlib import Path
from typing import Any
from retrospark.privacy.anonymizer import Anonymizer
from retrospark.privacy.secrets import redact_text

def _parse_tool_input(tool_name: str | None, input_data: Any, anonymizer: Anonymizer) -> dict:
    """Return a structured dict for a tool's input args, with paths/content anonymized."""
    if not isinstance(input_data, dict):
        return {"raw": anonymizer.text(str(input_data))}

    name = (tool_name or "").lower()

    # Claude Code tools
    if name in ("read", "edit"):
        return {"file_path": anonymizer.path(input_data.get("file_path", ""))}
    if name == "write":
        return {
            "file_path": anonymizer.path(input_data.get("file_path", "")),
            "content": anonymizer.text(input_data.get("content", "")),
        }
    if name == "bash":
        cmd, _ = redact_text(input_data.get("command", ""))
        return {"command": anonymizer.text(cmd)}
    if name == "grep":
        pattern, _ = redact_text(input_data.get("pattern", ""))
        return {"pattern": anonymizer.text(pattern), "path": anonymizer.path(input_data.get("path", ""))}
    if name == "glob":
        return {"pattern": input_data.get("pattern", ""), "path": anonymizer.path(input_data.get("path", ""))}
    if name == "task":
        return {"prompt": anonymizer.text(input_data.get("prompt", ""))}
    if name == "websearch":
        return {"query": anonymizer.text(input_data.get("query", ""))}
    if name == "webfetch":
        return {"url": anonymizer.text(input_data.get("url", ""))}
    if name == "apply_patch":
        return {"patch": anonymizer.text(input_data.get("patchText", ""))}
    if name == "codesearch":
        return {"query": anonymizer.text(input_data.get("query", ""))}

    # Codex tools
    if name == "exec_command":
        cmd, _ = redact_text(input_data.get("cmd", ""))
        return {"cmd": anonymizer.text(cmd)}
    if name == "shell_command":
        cmd, _ = redact_text(input_data.get("command", ""))
        return {
            "command": anonymizer.text(cmd),
            "workdir": anonymizer.path(input_data.get("workdir", "")),
        }
    if name == "write_stdin":
        return {
            "session_id": input_data.get("session_id"),
            "chars": anonymizer.text(input_data.get("chars", "")),
            "yield_time_ms": input_data.get("yield_time_ms"),
            "max_output_tokens": input_data.get("max_output_tokens"),
        }
    if name == "update_plan":
        plan = input_data.get("plan", [])
        return {
            "explanation": anonymizer.text(input_data.get("explanation", "")),
            "plan": [anonymizer.text(str(p)) if isinstance(p, str) else p for p in plan],
        }

    # Fallback: anonymize all string values
    return {k: anonymizer.text(str(v)) if isinstance(v, str) else v for k, v in input_data.items()}
