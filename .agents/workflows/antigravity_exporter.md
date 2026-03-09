---
description: Helps the Antigravity Agent export its current chat history into a standardized JSON format that RetroSpark can parse.
---

# Skill: Antigravity Data Exporter

## 🌟 When to Use

Use this skill when you are running as an Agent inside **Google Antigravity** and the user asks you to "save", "sync", or "export" the current session to RetroSpark, especially when direct log reading is blocked by encryption.

## ⚙️ How it Works

1. You utilize your internal session memory and file access to `~/.gemini/antigravity/brain/` to retrieve the dialogue history.
2. You export this history into a specifically structured JSON file located in the project's data directory.

## 🛠️ Instructions for the Agent

### 1. Identify the Session ID

Determine the current session's UUID (typically found in the `brain/` directory path or internal metadata).

### 2. Prepare the JSON Payload

Construct a JSON object with the following schema:

```json
{
  "session_id": "<UUID>",
  "project": "<Workspace Name>",
  "source": "antigravity",
  "model": "<Model Name>",
  "start_time": "<ISO8601 Timestamp>",
  "end_time": "<ISO8601 Timestamp>",
  "stats": {
    "user_messages": <Int>,
    "assistant_messages": <Int>,
    "tool_uses": <Int>,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "messages": [
    {
      "role": "user|assistant",
      "content": "<Text content>",
      "timestamp": "<ISO8601 Timestamp>",
      "thinking": "<Optional CoT>",
      "tool_uses": [
        {
          "tool": "<Name>",
          "input": {},
          "output": {"text": ""},
          "status": "success"
        }
      ]
    }
  ]
}
```

### 3. Save the Export

Keep original conversation history information and **NO CHANGE** at all.
Write the JSON content named as `chat_history_<UUID>.json` and save to `artifacts` folder.
