import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

def _make_stats() -> dict[str, int]:
    return {
        "user_messages": 0,
        "assistant_messages": 0,
        "tool_uses": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }

def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
    return None

def _update_time_bounds(metadata: dict[str, Any], timestamp: str | None) -> None:
    if timestamp is None:
        return
    if metadata["start_time"] is None:
        metadata["start_time"] = timestamp
    metadata["end_time"] = timestamp

def _safe_int(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return 0

def _load_json_field(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}

def _make_session_result(
    metadata: dict[str, Any], messages: list[dict[str, Any]], stats: dict[str, int],
) -> dict[str, Any] | None:
    if not messages:
        return None
    return {
        "session_id": metadata["session_id"],
        "model": metadata["model"],
        "git_branch": metadata.get("git_branch"),
        "start_time": metadata["start_time"],
        "end_time": metadata["end_time"],
        "messages": messages,
        "stats": stats,
    }
