import pytest
from retrospark.markdown.transformer import format_session_to_markdown

def test_format_session_to_markdown_basic():
    session = {
        "session_id": "test_123",
        "model": "claude-3.5-sonnet",
        "start_time": "2026-03-08T15:00:00Z",
        "end_time": "2026-03-08T15:05:00Z",
        "source": "claude",
        "project": "my_project",
        "stats": {
            "user_messages": 1,
            "assistant_messages": 1,
            "tool_uses": 0,
            "input_tokens": 100,
            "output_tokens": 50
        },
        "messages": [
            {"role": "user", "content": "Write a test function"},
            {"role": "assistant", "content": "Here is your test function..."}
        ]
    }
    
    md_str = format_session_to_markdown(session)
    
    # Check Frontmatter
    assert "---" in md_str
    assert "title: \"RetroSpark Session: my_project\"" in md_str
    assert "model: claude-3.5-sonnet" in md_str
    assert "source: claude" in md_str
    assert "session_id: test_123" in md_str
    assert "telemetry:" in md_str
    assert "user_messages: 1" in md_str
    
    # Check Body
    assert "# 🧠 Session: my_project" in md_str
    assert "## 👤 User" in md_str
    assert "Write a test function" in md_str
    assert "## 🤖 Assistant (`claude-3.5-sonnet`)" in md_str
    assert "Here is your test function..." in md_str

def test_format_session_with_tool_use():
    session = {
        "session_id": "tool_test",
        "model": "claude",
        "source": "claude",
        "project": "my_project",
        "messages": [
            {
                "role": "assistant", 
                "content": [{"type": "text", "text": "I am looking into this."}],
                "tool_uses": [
                    {"name": "Bash", "input": {"command": "ls -l"}}
                ]
            }
        ]
    }
    
    md_str = format_session_to_markdown(session)
    assert "I am looking into this." in md_str
    assert "<summary>🛠️ Tool Call: `Bash`</summary>" in md_str
    assert "ls -l" in md_str

def test_format_session_missing_data():
    # Should not crash on empty session
    md_str = format_session_to_markdown({})
    assert "title: \"RetroSpark Session: Unknown\"" in md_str
    assert "source: Unknown" in md_str
    assert "model: Unknown" in md_str
