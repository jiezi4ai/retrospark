import json
import sqlite3
import pytest
from retrospark.extractors.parser import discover_projects, parse_project_sessions
from retrospark.extractors import claude, common, tools

class MockAnonymizer:
    def path(self, p): return p
    def text(self, t): return t

@pytest.fixture
def mock_anonymizer():
    return MockAnonymizer()

class TestBuildProjectName:
    def test_documents_prefix(self):
        assert claude._build_project_name("-Users-alice-Documents-myproject") == "myproject"

    def test_home_prefix(self):
        assert claude._build_project_name("-home-bob-project") == "project"

    def test_standalone(self):
        assert claude._build_project_name("standalone") == "standalone"

    def test_bare_home(self):
        assert claude._build_project_name("-Users-alice") == "~home"

class TestNormalizeTimestamp:
    def test_string_passthrough(self):
        ts = "2025-01-15T10:00:00+00:00"
        assert common._normalize_timestamp(ts) == ts

    def test_int_ms_to_iso(self):
        result = common._normalize_timestamp(1706000000000)
        assert result is not None
        assert "2024" in result
        assert "T" in result

class TestParseToolInput:
    def test_bash_tool(self, mock_anonymizer):
        result = tools._parse_tool_input("Bash", {"command": "ls -la"}, mock_anonymizer)
        assert result["command"] == "ls -la"

    def test_exec_command_tool(self, mock_anonymizer):
        result = tools._parse_tool_input("exec_command", {"cmd": "ls -la"}, mock_anonymizer)
        assert result["cmd"] == "ls -la"

class TestExtractUserContent:
    def test_string_content(self, mock_anonymizer):
        entry = {"message": {"content": "Fix the bug"}}
        result = claude._extract_user_content(entry, mock_anonymizer)
        assert result == "Fix the bug"

    def test_list_content(self, mock_anonymizer):
        entry = {
            "message": {
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ]
            }
        }
        result = claude._extract_user_content(entry, mock_anonymizer)
        assert "Hello" in result
        assert "World" in result

class TestExtractAssistantContent:
    def test_text_blocks(self, mock_anonymizer):
        entry = {
            "message": {
                "content": [
                    {"type": "text", "text": "Here's the fix."},
                ]
            }
        }
        result = claude._extract_assistant_content(entry, mock_anonymizer, include_thinking=True)
        assert result["content"] == "Here's the fix."

    def test_thinking_included(self, mock_anonymizer):
        entry = {
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "Let me think..."},
                    {"type": "text", "text": "Done."},
                ]
            }
        }
        result = claude._extract_assistant_content(entry, mock_anonymizer, include_thinking=True)
        assert "Let me think..." in result["thinking"]

    def test_tool_uses(self, mock_anonymizer):
        entry = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/tmp/test.py"},
                    },
                ]
            }
        }
        result = claude._extract_assistant_content(entry, mock_anonymizer, include_thinking=True)
        assert result["tool_uses"][0]["tool"] == "Read"

class TestDiscoverProjects:
    def _disable_codex_opencode(self, tmp_path, monkeypatch):
        monkeypatch.setattr("retrospark.extractors.codex.CODEX_SESSIONS_DIR", tmp_path / "no-codex")
        monkeypatch.setattr("retrospark.extractors.codex.CODEX_ARCHIVED_DIR", tmp_path / "no-archived")
        monkeypatch.setattr("retrospark.extractors.codex._CodexParseState", type('PseudoState', (), {'_CODEX_PROJECT_INDEX': {}}))
        monkeypatch.setattr("retrospark.extractors.gemini.GEMINI_DIR", tmp_path / "no-gemini")
        monkeypatch.setattr("retrospark.extractors.opencode.OPENCODE_DB_PATH", tmp_path / "no-opencode.db")
        monkeypatch.setattr("retrospark.extractors.openclaw.OPENCLAW_AGENTS_DIR", tmp_path / "no-openclaw")
        monkeypatch.setattr("retrospark.extractors.kimi.KIMI_SESSIONS_DIR", tmp_path / "no-kimi")
        monkeypatch.setattr("retrospark.extractors.custom.CUSTOM_DIR", tmp_path / "no-custom")

    def test_with_projects(self, tmp_path, monkeypatch, mock_anonymizer):
        self._disable_codex_opencode(tmp_path, monkeypatch)
        projects_dir = tmp_path / "projects"
        proj = projects_dir / "-Users-alice-Documents-myapp"
        proj.mkdir(parents=True)

        # Write a valid session file
        session = proj / "abc-123.jsonl"
        session.write_text(
            '{"type":"user","timestamp":1706000000000,"message":{"content":"Hi"},"cwd":"/tmp"}\n'
            '{"type":"assistant","timestamp":1706000001000,"message":{"model":"m","content":[{"type":"text","text":"Hey"}],"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        )

        monkeypatch.setattr("retrospark.extractors.claude.PROJECTS_DIR", projects_dir)
        projects = discover_projects()
        assert len(projects) == 1
        assert projects[0]["display_name"] == "myapp"
        assert projects[0]["session_count"] == 1

    def test_parse_project_sessions(self, tmp_path, monkeypatch, mock_anonymizer):
        self._disable_codex_opencode(tmp_path, monkeypatch)
        projects_dir = tmp_path / "projects"
        proj = projects_dir / "test-project"
        proj.mkdir(parents=True)

        session = proj / "session1.jsonl"
        session.write_text(
            '{"type":"user","timestamp":1706000000000,"message":{"content":"Hello"},"cwd":"/tmp"}\n'
            '{"type":"assistant","timestamp":1706000001000,"message":{"model":"m","content":[{"type":"text","text":"Hi"}],"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        )

        monkeypatch.setattr("retrospark.extractors.claude.PROJECTS_DIR", projects_dir)
        sessions = parse_project_sessions("test-project", mock_anonymizer)
        assert len(sessions) == 1
        assert sessions[0]["project"] == "test-project"
