# Agent Interaction Data Format Knowledge Base

This document outlines the data storage paths, storage formats, and parsing mechanisms for various AI programming tools. This knowledge is crucial for building robust extraction pipelines in tools like RetroSpark and DataClaw.

## 1. Claude Code
- **Storage Path**: `~/.claude/projects/`
  - Directories inside typically use a hyphen-separated representation of the target project's absolute path (e.g., `-Users-alice-Documents-myproject`).
  - Contains `.jsonl` files (representing distinct sessions).
  - Subagents may store logs under a `subagents/` subdirectory.
- **Data Format**: `JSONL` (JSON Lines)
- **Parsing Mechanism**: 
  - Each line is a parsed JSON object representing an event.
  - User messages are under `{"type": "user", "message": {"content": "..."}}`.
  - Assistant messages use `{"type": "assistant", "message": {"content": [{"text": "...", "type": "text"}]}}`.
  - Tool calls emit `{"type": "tool_use", "name": "...", "input": {...}}`.

## 2. Codex
- **Storage Path**: `~/.codex/sessions/` (and archives in `~/.codex/archived_sessions/`)
- **Data Format**: `JSONL`
- **Parsing Mechanism**:
  - The first line explicitly sets session metadata via `{"type": "session_meta", "payload": {"id": "...", "cwd": "..."}}`.
  - Subsequent lines trigger `event_msg` (e.g., user inputs or token constraints) and `response_item` (e.g., reasoning stages, assistant text blocks).
  - Tool execution is defined under `{"type": "function_call", "name": "...", "arguments": "..."}`.

## 3. Gemini CLI
- **Storage Path**: `~/.gemini/tmp/`
  - Project directories are defined by the **SHA-256 hash** of the absolute working directory path.
  - Inside the hashed directory, sessions are in `chats/session-*.json`.
- **Data Format**: `JSON` (Single File per Session)
- **Parsing Mechanism**:
  - Contains a single JSON object. The interaction history is a list under the `messages` key.
  - Tool execution structures exist under `toolCalls`.
  - Because paths are hashed, parsing tools must reconstruct the original path either by pre-hashing known system directories or by extracting the deepest path mentioned within the `toolCalls` payloads.

## 4. OpenCode
- **Storage Path**: `~/.local/share/opencode/opencode.db`
- **Data Format**: `SQLite 3 Database`
- **Parsing Mechanism**:
  - The database separates interactions into three primary tables: `session`, `message`, and `part`.
  - `session`: Contains `id`, `directory`, `time_created`, `time_updated`.
  - `message`: Linked via `session_id`, stores the `role` and `model` in a JSON-encoded `data` column.
  - `part`: Linked via `message_id`, stores actual text elements, reasoning blocks, and tool executions.

## 5. OpenClaw
- **Storage Path**: `~/.openclaw/agents/`
- **Data Format**: `JSONL`
- **Parsing Mechanism**:
  - Functions identically to Claude Code's schema but is scoped to OpenClaw's own hidden directory and `agents` categorization.

## 6. Google Antigravity
- **Storage Path**: `~/.gemini/antigravity/brain/<conversation-id>/`
- **Data Format**: `JSONL` / `.txt` logs within `.system_generated/logs/` and Markdown artifacts within the root of the conversation ID.
- **Parsing Mechanism**:
  - A comprehensive system log tracking explicit interactions and sub-agent invocations. System-generated `.jsonl` files hold structured thought traces.
  - Important user-facing outputs and plans are rendered as actual Markdown files (`.md`) within the same directory, enabling immediate human readability without post-processing.
