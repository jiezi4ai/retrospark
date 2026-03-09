import os
import json
import sqlite3
import hashlib
from pathlib import Path

# Allows overriding for testing purposes
MOCK_HOME = Path(os.environ.get("MOCK_HOME", "/tmp/retrospark_mock_home"))

def reset_mock_home():
    if MOCK_HOME.exists():
        import shutil
        shutil.rmtree(MOCK_HOME)
    MOCK_HOME.mkdir(parents=True, exist_ok=True)

def generate_claude_mock():
    proj_dir = MOCK_HOME / ".claude" / "projects" / "my-claude-project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    session_file = proj_dir / "claude_session.jsonl"
    with open(session_file, "w") as f:
        # Extractor looks for cwd and sessionId in early entries
        f.write(json.dumps({"type": "user", "timestamp": 1700000000000, "cwd": "/home/user/my-claude-project", "sessionId": "claude-123", "message": {"content": "Hello"}}) + "\n")
        f.write(json.dumps({"type": "assistant", "timestamp": 1700000001000, "message": {"model": "claude-3-5-sonnet", "content": [{"type": "text", "text": "Hi!"}], "usage": {"input_tokens": 10, "output_tokens": 5}}}) + "\n")

def generate_codex_mock():
    sess_dir = MOCK_HOME / ".codex" / "sessions"
    sess_dir.mkdir(parents=True, exist_ok=True)
    session_file = sess_dir / "codex_session.jsonl"
    with open(session_file, "w") as f:
        f.write(json.dumps({"type": "session_meta", "timestamp": 1700000000000, "payload": {"id": "codex-123", "cwd": "/home/user/my-codex-project", "model_provider": "anthropic"}}) + "\n")
        f.write(json.dumps({"type": "event_msg", "timestamp": 1700000001000, "payload": {"type": "user_message", "message": "Help me"}}) + "\n")
        f.write(json.dumps({"type": "event_msg", "timestamp": 1700000002000, "payload": {"type": "agent_message", "message": "Yes, I can."}}) + "\n")

def generate_gemini_mock():
    # Gemini uses hashed dir name
    mock_cwd = "/home/user/my-gemini-project"
    cwd_hash = hashlib.sha256(mock_cwd.encode()).hexdigest()
    
    chats_dir = MOCK_HOME / ".gemini" / "tmp" / cwd_hash / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    session_file = chats_dir / "session-gemini-123.json"
    data = {
        "sessionId": "gemini-123",
        "startTime": "2026-03-08T10:00:00Z",
        "lastUpdated": "2026-03-08T10:05:00Z",
        "messages": [
            {
                "type": "user",
                "timestamp": "2026-03-08T10:00:01Z",
                "content": "Hello Gemini"
            },
            {
                "type": "gemini",
                "timestamp": "2026-03-08T10:00:10Z",
                "model": "gemini-2.0-flash",
                "content": "Hi there!",
                "tokens": {"input": 100, "output": 50},
                "toolCalls": [
                    {
                        "name": "run_shell_command",
                        "args": {"command": "ls"},
                        "status": "success",
                        "result": [{"functionResponse": {"response": {"output": "Command: ls\nDirectory: .\nOutput: file1\nExit Code: 0"}}}]
                    }
                ]
            }
        ]
    }
    with open(session_file, "w") as f:
        json.dump(data, f)

def generate_opencode_mock():
    db_dir = MOCK_HOME / ".local" / "share" / "opencode"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "opencode.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE session (id TEXT, directory TEXT, time_created TEXT, time_updated TEXT)")
    cursor.execute("CREATE TABLE message (id INTEGER PRIMARY KEY, session_id TEXT, data TEXT, time_created TEXT)")
    cursor.execute("CREATE TABLE part (id INTEGER, message_id INTEGER, data TEXT, time_created TEXT)")
    
    cursor.execute("INSERT INTO session VALUES ('oc-123', '/home/user/my-opencode-project', '2026-03-08T10:00:00Z', '2026-03-08T10:05:00Z')")
    # User message
    cursor.execute("INSERT INTO message (id, session_id, data, time_created) VALUES (1, 'oc-123', '{\"role\": \"user\"}', '2026-03-08T10:00:05Z')")
    cursor.execute("INSERT INTO part (message_id, data) VALUES (1, '{\"type\": \"text\", \"text\": \"Fix it\"}')")
    # Assistant message
    cursor.execute("INSERT INTO message (id, session_id, data, time_created) VALUES (2, 'oc-123', '{\"role\": \"assistant\", \"model\": {\"providerID\": \"openai\", \"modelID\": \"gpt-4o\"}, \"tokens\": {\"input\": 10, \"output\": 20}}', '2026-03-08T10:01:00Z')")
    cursor.execute("INSERT INTO part (message_id, data) VALUES (2, '{\"type\": \"text\", \"text\": \"Fixed.\"}')")
    
    conn.commit()
    conn.close()

def generate_openclaw_mock():
    agent_dir = MOCK_HOME / ".openclaw" / "agents" / "my-agent" / "sessions"
    agent_dir.mkdir(parents=True, exist_ok=True)
    session_file = agent_dir / "openclaw_session.jsonl"
    with open(session_file, "w") as f:
        # First line MUST be type: "session"
        f.write(json.dumps({"type": "session", "id": "claw-123", "cwd": "/home/user/my-openclaw-project", "timestamp": "2026-03-08T10:00:00Z"}) + "\n")
        f.write(json.dumps({"type": "message", "timestamp": "2026-03-08T10:00:05Z", "message": {"role": "user", "content": "Help"}}) + "\n")
        f.write(json.dumps({"type": "message", "timestamp": "2026-03-08T10:00:10Z", "message": {"role": "assistant", "model": "sonnet-3.7", "content": [{"type": "text", "text": "OK"}]}}) + "\n")

def generate_kimi_mock():
    # Kimi has a sessions/<hash>/<session_uuid>/context.jsonl structure
    work_dir = "/home/user/my-kimi-project"
    project_hash = hashlib.md5(work_dir.encode()).hexdigest()
    
    # Kimi config
    kimi_dir = MOCK_HOME / ".kimi"
    kimi_dir.mkdir(parents=True, exist_ok=True)
    with open(kimi_dir / "kimi.json", "w") as f:
        json.dump({"work_dirs": [{"path": work_dir}]}, f)
        
    sess_dir = kimi_dir / "sessions" / project_hash / "sess-123"
    sess_dir.mkdir(parents=True, exist_ok=True)
    with open(sess_dir / "context.jsonl", "w") as f:
        f.write(json.dumps({"role": "user", "content": "Hello Kimi"}) + "\n")
        f.write(json.dumps({"role": "assistant", "content": [{"type": "text", "text": "Hi!"}]}) + "\n")

def generate_custom_mock():
    custom_dir = MOCK_HOME / ".dataclaw" / "custom" / "my-custom-project"
    custom_dir.mkdir(parents=True, exist_ok=True)
    session_file = custom_dir / "custom_session.jsonl"
    with open(session_file, "w") as f:
        f.write(json.dumps({
            "session_id": "cust-123",
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "custom hello"}],
            "start_time": "2026-03-08T10:00:00Z",
            "end_time": "2026-03-08T10:01:00Z"
        }) + "\n")

def generate_antigravity_mock():
    # .gemini/antigravity/brain/<uuid>/.system_generated/logs/
    ag_dir = MOCK_HOME / ".gemini" / "antigravity" / "brain" / "project-uuid" / ".system_generated" / "logs"
    ag_dir.mkdir(parents=True, exist_ok=True)
    session_file = ag_dir / "session_1.jsonl"
    with open(session_file, "w") as f:
        f.write(json.dumps({"role": "user", "timestamp": "2026-03-08T10:00:00Z", "content": "antigravity msg"}) + "\n")
        f.write(json.dumps({"role": "assistant", "timestamp": "2026-03-08T10:00:05Z", "content": [{"text": "response"}]}) + "\n")

def generate_all():
    reset_mock_home()
    generate_claude_mock()
    generate_codex_mock()
    generate_gemini_mock()
    generate_opencode_mock()
    generate_openclaw_mock()
    generate_kimi_mock()
    generate_custom_mock()
    generate_antigravity_mock()
    print(f"Mock data generated in {MOCK_HOME}")

if __name__ == "__main__":
    generate_all()
