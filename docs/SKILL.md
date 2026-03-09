---
name: retrospark
description: Review, rethink, reinvent with AI. Saves your current conversation state, thoughts, and extracted code as structured Markdown notes into the user's local digital repository (automatically versioned with Git).
---

# RetroSpark: Review, rethink, reinvent with AI

## 🌟 When to Use

Use `retrospark` when the user explicitly asks you to "save my progress", "export our chat", "archive this session", or "take a note of this". The user relies on this tool to build a long-term knowledge base.

## ⚙️ How it Works

1. RetroSpark is a CLI tool (`retrospark`) installed on this machine.
2. It interacts entirely via **JSON output**. Do not explain the JSON output to the user unless they ask; just follow the `next_steps` internally.

## 🛠️ Instructions for the Agent

1. **Invoke the Tracker:**
   Run `retrospark sync --source <your_assistant_name_here> --json` (e.g. `retrospark sync --source antigravity --json` or `retrospark sync --source claude --json`).
   *Support sources include: `antigravity`, `claude`, `codex`, `gemini`, `opencode`, `openclaw`, `kimi`, `all`.*

    > [!IMPORTANT]
    > **For Antigravity Source**: Google Antigravity chat histories are encrypted. You **MUST** run the `antigravity_exporter` skill (located at `.agents/workflows/antigravity_exporter.md`) FIRST to convert your memory to JSON. Confirm that the JSON must be saved into the hardcoded `./artifacts/` directory before running `retrospark sync`.

   *If you know the specific project hash or folder you are currently in, append `--project <dir_name>`.*

2. **Read the JSON Response:**
   RetroSpark will return a JSON object (because you passed the `--json` flag).
   - If `status == "success"`, it means it successfully extracted the recent session, scrubbed PII via high-entropy scanning, formatted it into beautiful Markdown with Frontmatter analytics, and committed + pushed it to the user's configured GitHub repo.
   - If `status == "error"`, read the `message` field and inform the user. It may say the chat history JSON data is missing, asking you to run `retrospark init --json` first.

3. **Follow the Workflows:**
   - If the JSON has a `next_command`, run it automatically.
   - If the JSON has `next_steps`, read them silently to know what to do next.

## 🤫 Privacy First

RetroSpark runs natively on the user's machine. It performs local Git commits. It scrubs secrets (JWTs, AWS keys) automatically. You do NOT need to manually delete code from context. Just run the `sync` command.
