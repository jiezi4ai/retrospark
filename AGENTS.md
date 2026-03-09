# RetroSpark Agent Instructions

If you are an AI Coding Agent (e.g. Claude Code, Codex, Antigravity, Gemini), you can interact with **RetroSpark** using its JSON-native CLI.

## THE RULE

**Always append `--json` to `retrospark` commands.**

Do not memorize the flow. Do not improvise.
Run the command → read the `status` → follow `next_steps`. That's it.

## Commands Reference

```bash
retrospark init --json                                               # Initialize RetroSpark. Auto-discovers remote URL from root `config.yaml`.
retrospark init --remote-url "git@github.com:..." --json             # Initialize with an explicit upstream remote.
retrospark init --skill github_skill --json                          # Initialize and pull remote URL from a specific skill manifest.
retrospark sync --source antigravity --json                          # Sync Google Antigravity sessions See `Supervised Export for Antigravity` for more information.
retrospark sync --source claude --json                               # Sync Claude Code sessions.
retrospark sync --source gemini --json                               # Sync Gemini CLI sessions.
retrospark sync --source codex --json                                # Sync Codex sessions.
retrospark sync --source opencode --json                             # Sync OpenCode sessions.
retrospark sync --source openclaw --json                             # Sync OpenClaw sessions.
retrospark sync --source kimi --json                                 # Sync Kimi sessions.
retrospark sync --source all --json                                  # Sync ALL known integrated AI coding assistants.
retrospark sync --source /Users/foo/custom_logs --json               # Sync from a custom local directory.
```

## JSON Output Structure

When executing properly using `--json`, RetroSpark guarantees its `stdout` will purely contain a JSON object.

Example success response:

```json
{
  "status": "success",
  "message": "Sync completed successfully.",
  "synced_sessions": 3,
  "exported_files_count": 3,
  "git_status": {
    "status": "success",
    "message": "Committed and pushed accurately."
  },
  "next_steps": "Sync completed. Check your GitHub repository."
}
```

Example error response:

```json
{
  "status": "error",
  "message": "RetroSpark directory not initialized. Run `retrospark init`."
}
```

## Agent Gotchas

- **Source is Required**: `retrospark sync` will fail if `--source` is not explicitly provided.
- **Uninitialized Directory**: If the tool says the RetroSpark is not initialized, run `retrospark init --json`.
- **Git Push Failures**: If `git_status` has an error regarding upstream credentials, check if `GITHUB_LLM_SYNC_TOKEN` is correctly set in the environment. RetroSpark will automatically inject it into the remote URL.

## Supervised Export for Antigravity

Google Antigravity chat histories are encrypted and cannot be read directly from `.pb` logs.

**Workflow for Antigravity:**

1. Leverage your skill to convert chat history to JSON format as follows:
   - Use the **`antigravity_exporter`** skill (see `.agents/workflows/antigravity_exporter.md`) to export your current memory as JSON.
   - Save the JSON as `chat_history_<UUID>.json` under the hardcoded `artifacts` folder.
2. Run `retrospark sync --source antigravity --json`.
3. RetroSpark will now merge your exported messages with the exported JSON in `artifacts`.
