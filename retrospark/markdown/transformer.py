from typing import Any, Dict, List
from datetime import datetime
import json

def format_session_to_markdown(session: Dict[str, Any]) -> str:
    """Convert a parsed session dictionary into a formatted Markdown string."""
    
    # 1. Extract metadata and stats
    session_id = session.get("session_id", "Unknown")
    model = session.get("model", "Unknown")
    start_time = session.get("start_time")
    end_time = session.get("end_time")
    stats = session.get("stats", {})
    source = session.get("source", "Unknown")
    project = session.get("project", "Unknown")
    
    # Format Date
    date_str = "Unknown Date"
    if start_time:
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            date_str = start_time

    # 2. Build YAML Frontmatter (Metrics & Telemetry dashboard)
    md_lines = []
    md_lines.append("---")
    md_lines.append(f"title: \"RetroSpark Session: {project}\"")
    md_lines.append(f"date: {date_str}")
    md_lines.append(f"model: {model}")
    md_lines.append(f"source: {source}")
    md_lines.append(f"session_id: {session_id}")
    
    # Telemetry
    md_lines.append("telemetry:")
    md_lines.append(f"  user_messages: {stats.get('user_messages', 0)}")
    md_lines.append(f"  assistant_messages: {stats.get('assistant_messages', 0)}")
    md_lines.append(f"  tool_uses: {stats.get('tool_uses', 0)}")
    md_lines.append(f"  input_tokens: {stats.get('input_tokens', 0)}")
    md_lines.append(f"  output_tokens: {stats.get('output_tokens', 0)}")
    md_lines.append("---")
    md_lines.append("")
    
    # 3. Main Title
    md_lines.append(f"# 🧠 Session: {project}")
    md_lines.append(f"**Date:** {date_str} | **Model:** `{model}`")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    # 4. Process Messages
    messages = session.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if role == "user":
            md_lines.append("## 👤 User")
            md_lines.append("")
            # Handle text content
            if isinstance(content, str):
                md_lines.append(content.strip())
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            md_lines.append(block.get("text", "").strip())
                            md_lines.append("")
                        # Minimal handling for tool_results, if they exist in user messages
                        elif block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id", "unknown")
                            is_error = block.get("is_error", False)
                            status = "❌ Error" if is_error else "✅ Success"
                            md_lines.append(f"<details><summary>🔧 Tool Result [{status}]: `{tool_use_id}`</summary>")
                            md_lines.append("")
                            md_lines.append("```text")
                            
                            res_content = block.get("content", "")
                            if isinstance(res_content, str):
                                md_lines.append(res_content.strip())
                            elif isinstance(res_content, list):
                                for part in res_content:
                                    if part.get("type") == "text":
                                        md_lines.append(part.get("text", "").strip())
                            md_lines.append("```")
                            md_lines.append("</details>")
                            md_lines.append("")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
            
        elif role == "assistant":
            md_lines.append(f"## 🤖 Assistant (`{model}`)")
            md_lines.append("")
            
            # Formatted text content
            text_content = ""
            if isinstance(content, str):
                text_content = content
            elif isinstance(content, list):
                # DataClaw sometimes passes tool_calls separately or embedded, we need to extract text
                texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                text_content = "\n\n".join(texts)
                
            if text_content:
                md_lines.append(text_content.strip())
                md_lines.append("")
            
            # Formatted Tool Calls (from Claude/Opencode)
            tool_uses = msg.get("tool_uses", [])
            for tool in tool_uses:
                tool_name = tool.get("name", "unknown")
                tool_input = tool.get("input", {})
                
                md_lines.append(f"<details><summary>🛠️ Tool Call: `{tool_name}`</summary>")
                md_lines.append("")
                md_lines.append("```json")
                try:
                    md_lines.append(json.dumps(tool_input, indent=2, ensure_ascii=False))
                except Exception:
                    md_lines.append(str(tool_input))
                md_lines.append("```")
                md_lines.append("</details>")
                md_lines.append("")
            
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

    return "\n".join(md_lines)
