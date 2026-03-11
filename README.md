# RetroSpark

> **Review, rethink, reinvent with AI.**
> RetroSpark captures your conversations, thoughts, and generated code from AI coding assistants and saves them as structured Markdown notes into your personal local repository (automatically versioned with Git).

Turn your **Google Antigravity**, Claude Code, Codex, Gemini CLI, OpenCode, OpenClaw, and Kimi conversation history into beautiful, organized Markdown and sync it to a private Git repository with a single command. RetroSpark parses session logs, redacts secrets and PII, and outputs a ready-to-view knowledge base.

---

## 🚀 Quick Start: Installation & Setup

RetroSpark consists of two parts: a **globally installed CLI tool**, and a **project-level Agent Skill** (so your AI actually knows how to use the CLI).

### STEP 1 — INSTALL THE CLI (GLOBAL)

Install the RetroSpark CLI system-wide. This gives your machine the `retrospark` command.

```bash
pip install retrospark
# or, for isolated environments:
pipx install retrospark
```

*The CLI is now available globally across your machine.*

### STEP 2 — INSTALL THE SKILL (LOCAL TO PROJECT)

AI Coding Agents operate contextually. To let your Agent know about RetroSpark, you must "install the skill" into your current project folder.

Run this command **in any project directory** where you plan to use an AI Assistant:

```bash
# For Claude Code
retrospark install-skill claude

# For Google Antigravity, Gemini CLI, OpenCode, etc. (Open Standard Agent Skills)
retrospark install-skill antigravity

# Or, just install for all other known local agents at once
retrospark install-skill others
```

**🤔 What did this just do?**
This command simply unpacks a tiny `SKILL.md` instruction file into your current project's hidden agent folder (like `.claude/skills/retrospark/SKILL.md` or `.agents/skills/retrospark/SKILL.md`).

- **Global Tool:** `retrospark` runs anywhere.
- **Local Skill:** The Agent only "sees" the tool if the `SKILL.md` is in its current workspace. If you switch to a brand new project tomorrow, just run `retrospark install-skill others` again to give the Agent knowledge of the tool there.

### STEP 3 — INITIAL CONFIGURATION

RetroSpark needs to know where to backup your chats. 
Create your configuration file in the project directory, or globally at `~/.retrospark/config.yaml`:

```bash
cp "config_copy.yaml" config.yaml
```

Edit `config.yaml` to update `github_repo.remote_url` to your private backup repository.
Ensure the `GITHUB_LLM_SYNC_TOKEN` environment variable is exported in your shell with a GitHub Personal Access Token (with repo write access).

### STEP 4 — START USING IT

Just talk to your agent. Say:
> **"Please save my progress"**
> *or* **"Export our chat history"**

The Agent will automatically read the local `SKILL.md` and trigger the global `retrospark sync` command to process and backup your conversation.

---

<details>
<summary><b>Manual usage (without an agent) / Advanced Configuration</b></summary>

## Manual Commands

You can run RetroSpark entirely manually.

```bash
# Initialize inside a data folder
retrospark init

# Or manually specify an upstream Git repo (overrides config.yaml)
retrospark init --remote-url "https://github.com/your-username/your-git-repo.git"

# Sync all sessions for a specific AI tool
retrospark sync --source claude
retrospark sync --source kimi

# Sync all sessions for Google Antigravity
retrospark sync --source antigravity

# Sync from a custom local folder containing .jsonl history logs
retrospark sync --source /path/to/my/custom_path
```

### Supported Sources

When using `--source`, you must provide the tool's identifier. The recognized sources are:

- `antigravity` (Google Antigravity Agent - **Requires pre-export via `antigravity_exporter` skill due to encryption**)
- `claude` (Claude Code)
- `codex` (Codex)
- `gemini` (Gemini CLI)
- `opencode` (OpenCode)
- `openclaw` (OpenClaw)
- `kimi` (Kimi)
- `all` (Scans and extracts from all supported native tools automatically)
- `<local_folder_path>` (Any absolute or relative path to a directory containing `.jsonl` session files)

</details>

<details>
<summary><b>Alternative: Manual Prompt Injection</b></summary>

If you do not wish to install the skill globally using `retrospark install-skill`, you can manually paste the following instructions into your agent to force it to use it:

```markdown
Help me export and backup our conversation history using RetroSpark.

STEP 1 — VERIFY ENVIRONMENT
  Check if `retrospark` is available in the environment path. If not, stop and inform the user to install it.

STEP 2 — INITIALIZE YOUR RetroSpark
  Run `retrospark init --json`
  RetroSpark will automatically discover your remote repository from `config.yaml` if present. This configures the local `.retrospark/interaction` directory for Markdown storage and Git tracking.

STEP 3 — SYNC SESSIONS
  For manual invocation: `retrospark sync --source <your_ai_tool> --json`
  (e.g., `retrospark sync --source claude --json`)
   RetroSpark will scan history logs, sanitize PII, integrate project artifacts, and Git Commit + Push automatically.
  
  Read the JSON output:
  - If `status == "success"`, inform the user that the sync is complete.
  - If `status == "error"`, read the `message` field and inform the user of the failure.

IMPORTANT: Always pass the `--json` flag for machine-readable output. 
```

</details>

<details>
<summary><b>Privacy & What gets exported</b></summary>

| Data | Included | Notes |
| :--- | :--- | :--- |
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
5. **Automated Auth** — RetroSpark automatically detects the `GITHUB_LLM_SYNC_TOKEN` environment variable and injects it into GitHub HTTPS URLs, so you don't have to store plain-text tokens in your config files.

</details>

## License

MIT
