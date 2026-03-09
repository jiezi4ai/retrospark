# RetroSpark Source Data: Original vs. Processed Guide

本文档整合了 RetroSpark 支持的各 AI 工具源（Source）的原始数据格式与处理后的标准化数据格式。这对于理解 RetroSpark 的数据抽取逻辑、隐私脱敏流程以及最终的数据资产模型至关重要。

---

## 1. 原始数据格式 (Original Source Data)

RetroSpark 直接从各 AI 开发工具的本地存储目录中提取原始日志。

### 1.1 Claude Code

- **存储路径**: `~/.claude/projects/`
- **数据格式**: `JSONL` (JSON Lines)
- **特征**: 每个项目对应一个目录（名称经脱敏处理），目录下包含多个 `.jsonl` 会话文件。

### 1.2 Codex

- **存储路径**: `~/.codex/sessions/`
- **数据格式**: `JSONL`
- **特征**: 首行包含 `session_meta` 负载，后续行为 `event_msg` 或 `response_item`。

### 1.3 Gemini CLI

- **存储路径**: `~/.gemini/tmp/`
- **数据格式**: `JSON` (单文件)
- **特征**: 目录名是工作目录路径的 SHA-256 哈希。包含完整的对话列表和工具调用。

### 1.4 OpenCode

- **存储路径**: `~/.local/share/opencode/opencode.db`
- **数据格式**: `SQLite 3` 数据库
- **特征**: 通过 `session`, `message`, `part` 三张表关联存储。

### 1.5 OpenClaw

- **存储路径**: `~/.openclaw/agents/`
- **数据格式**: `JSONL`
- **特征**: 结构与 Claude Code 类似，但作用域在 OpenClaw 隐藏目录下。

### 1.6 Google Antigravity

- Google Antigravity 的部分数据经过了加密处理，具体的说明和处理可参见`source_antigravity_data_guide.md`文档。

---

## 2. 标准化处理后的格式 (Unified Processed Format)

RetroSpark 将上述异构的原始数据统一转换为标准化的 **Session 对象**。

### 2.1 标准 Session 数据模板

处理后的数据通常以 JSON 格式存储或在内存中流动，结构如下：

```json
{
  "session_id": "UUID",
  "project": "Display Name",
  "source": "claude|gemini|antigravity|...",
  "model": "model-name",
  "start_time": "ISO8601 Timestamp",
  "end_time": "ISO8601 Timestamp",
  "stats": {
    "user_messages": 0,
    "assistant_messages": 0,
    "tool_uses": 0,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "messages": [
    {
      "role": "user|assistant",
      "content": "Anonymized Text",
      "timestamp": "ISO8601 Timestamp",
      "thinking": "CoT if available",
      "tool_uses": []
    }
  ]
}
```

### 2.2 数据一致性保证

- **统一模型**: 所有的 extractor 都遵循 `common.py` 定义的数据模型。
- **隐私脱敏**: 所有 `content` 和 `path` 都会经过 `Anonymizer` 处理，确保无敏感信息泄露。
- **工具调用归一化**: 无论原始工具调用是何种格式（如 `claude` 的 `tool_use` 块或 `gemini` 的 `toolCalls`），都会被转化为统一的 `tool_uses` 列表。

---

## 3. 原始与处理后的映射关系摘要

| Source | 原始格式 | 提取关键点 | 处理后输出 |
| :--- | :--- | :--- | :--- |
| **Claude** | JSONL | `type: user/assistant` | 标准 Session |
| **Gemini** | JSON | `messages` 列表 + SHA 哈希路径恢复 | 标准 Session |
| **OpenCode** | SQLite | 跨表 SQL 联查 (`part` 表提取内容) | 标准 Session |
| **Antigravity** | JSONL/MD | 提取 `.system_generated` 下的日志 | 标准 Session |
| **Codex** | JSONL | 解析 `response_item` 逻辑 | 标准 Session |

---

## 4. 总结

RetroSpark 的核心价值在于将各种不同厂商、不同存储形态的“原始碎片”（Raw Data）收敛为高度一致、可版本化、易于阅读的“数字资产”（Processed Session）。这种从原始到标准化的转变，是构建个人 AI 知识库的基础。
