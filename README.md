# RetroSpark

> **Your Local Digital Second Brain**

RetroSpark captures your conversations, thoughts, and generated code from AI coding assistants and saves them as structured Markdown notes into your personal local repository (automatically versioned with Git).

## Give this to your agent

Paste the following instructions into your preferred coding agent (e.g. Claude Code, Codex, Gemini CLI, OpenCode, OpenClaw, or Google Antigravity):

```
Help me export and backup our conversation history using RetroSpark.

STEP 1 — INSTALL OR VERIFY
  Command `retrospark` should be available in the environment.

STEP 2 — INITIALIZE YOUR BRAIN
  Run `retrospark init --json`
  RetroSpark will automatically discover your remote repository from `config.yaml` if present. This configures the local `.retrospark/brain` directory for Markdown storage and Git tracking.

STEP 3 — SYNC SESSIONS
  For manual invocation: `retrospark sync --source <your_ai_tool> --json`
  (e.g., `retrospark sync --source claude --json`, `retrospark sync --source antigravity --json`)
   RetroSpark will scan history logs, sanitize PII, integrate project artifacts (plans, logs) into the final Markdown, and Git Commit + Push automatically.
  
  Read the JSON output:
  - If `status == "success"`, inform the user that the sync is complete.
  - If `status == "error"`, read the `message` field and inform the user of the failure.

IMPORTANT: Always pass the `--json` flag for machine-readable output. 
```

## Manual Usage (Without an Agent)

RetroSpark includes built-in TTY/Human detection. If you run `retrospark` commands yourself in the terminal, it outputs beautiful, colored, and formatted conversational text instead of JSON!

### Quick start

```bash
# Initialize your Markdown brain and link a remote Git repo (optional)
retrospark init

# Sync all sessions for a specific AI tool (e.g., Claude Code)
retrospark sync --source claude

# Sync all sessions for Google Antigravity
retrospark sync --source antigravity

# Sync from a custom local folder containing .jsonl history logs
retrospark sync --source /path/to/my/custom_logs
```

### Supported Sources
When using `--source`, you must provide the tool's identifier. The recognized sources are:
- `antigravity` (Google Antigravity Agent)
- `claude` (Claude Code)
- `codex` (Codex)
- `gemini` (Gemini CLI)
- `opencode` (OpenCode)
- `openclaw` (OpenClaw)
- `kimi` (Kimi)
- `all` (Scans and extracts from all supported native tools automatically)
- `<local_folder_path>` (Any absolute or relative path to a directory containing `.jsonl` session files)

## What gets exported

| Data | Included | Notes |
|------|----------|-------|
| User messages | Yes | Full text |
| Assistant responses | Yes | Full text output |
| Extended thinking | Yes | Agent Reasoning |
| Token usage | Yes | Analytics summarized in YAML frontmatter |
| Model & metadata | Yes | Appended to YAML fields |

### Privacy & Redaction

RetroSpark applies multiple layers of protection LOCALLY before generating your Markdown:
1. **Path anonymization** — File paths stripped to relative structures.
2. **Secret detection** — Regex patterns catch JWT tokens, API keys, private keys, etc.
3. **Entropy analysis** — Long high-entropy strings in quotes are flagged as potential secrets.
4. **Local Git** — Your data never leaves your machine unless you explicitly configure a remote upstream Git payload during `retrospark init`.

## License
MIT
