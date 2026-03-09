# Google Antigravity 数据全解析与集成指南

Google Antigravity 是一个“Agent-first”的 AI 编程 IDE。由于其独特的架构，其交互数据的存储和提取具有一定的复杂性（部分加密，部分明文）。本文档整合了 Antigravity 的数据分布特征与标准的提取/导出方案。

---

## 一、 数据地理图谱：交互信息存储在哪里？

Antigravity 的核心数据主要分布在本地三个关键区域：

### 1. 对话历史 (Chat History) —— 【加密区】

- **路径**：`~/.gemini/antigravity/conversations/`
- **格式**：UUID 命名的 **.pb (Protocol Buffers)** 文件。
- **状态**：**已加密**。密钥由系统级 Secret Storage 管理，外部工具无法直接解码。

### 2. 全局大脑与构件 (Brain / Artifacts) —— 【明文区】

- **路径**：`~/.gemini/antigravity/brain/<Session-UUID>/`
- **内容**：存放 Agent 生成的所有构件（`task.md`, `implementation_plan.md`, `walkthrough.md`）以及 `.system_generated/logs/` 下的结构化日志。
- **状态**：**全明文**。这是 RetroSpark 提取技术架构和任务状态的核心来源。

### 3. IDE 索引与工作区状态 —— 【结构化数据库】

- **路径**：`~/.config/Antigravity/User/globalStorage/state.vscdb`
- **格式**：SQLite 数据库。
- **内容**：包含会话的元数据索引，可用户关联 UUID 与具体的工作区名称。

---

## 二、 核心痛点：如何突破 .pb 加密屏障？

由于原始对话日志（.pb）不可读，RetroSpark 采用了“由内而外”的**双重提取方案**：

### 方案 A：主动扫描 Brain 目录 (推荐)

RetroSpark 直接读取 `brain/` 下的明文 Markdown 文件。这种方式虽然无法获取原始的每一句对话，但能获取到**最有价值的阶段性总结和执行计划**。

### 方案 B：Agent 引导式导出 (完整对话恢复)

利用 Antigravity Agent 自身的系统权限，直接让它将当前的内存上下文导出为标准 JSON。

#### 核实过的导出 Prompt

```text
请利用你的系统权限（如读取内部 session 状态或对话日志）将本会话的【聊天历史】完整导出。

由于外部工具无法直接解析加密的 .pb 文件，我需要你将对话内容转化为标准的 JSON 格式。请生成一个包含以下结构的 JSON 对象：

{
  "session_id": "<当前会话 UUID>",
  "project": "<当前工作区名称>",
  "source": "antigravity",
  "model": "<当前使用的模型名称>",
  "messages": [
    {
      "role": "user/assistant",
      "content": "<原文>",
      "timestamp": "<时间戳>",
      "thinking": "<思考过程>",
      "tool_uses": [...]
    }
  ]
}

要求：
1. 【仅导出聊天历史】：利用内部状态还原。
2. 确保 `tool_uses` 完整。
3. 将生成的 JSON 文件命名为 `chat_history_<uuid>.json` 并保存到 `config.yaml` 中 `antigravity.history_path` 指定的目录下（当前为 `./artifacts/`）。
4. 细节还原，不做任何调整。
5. 导出过程中不要使用其它任何的 tools、skills 或 mcp servers。
```

---

## 三、 数据整合逻辑

RetroSpark 在处理 Antigravity 数据时，会执行以下对齐操作：

1. **ID 匹配**：将导出的 JSON 中的 `session_id` 与 `brain/` 下的目录名进行关联。
2. **内容注入**：如果检测到导出的 JSON，RetroSpark 会将其中的 `messages` 列表注入到对应的 Session 对象中，从而完美弥补 `.pb` 加密导致的对话内容缺失。
3. **元数据对齐**：通过 `state.vscdb` 获取会话的显示名称，使输出的 Markdown 具有人类可读的标题。

---

## 四、 总结与操作建议

- **对于日常备份**：RetroSpark 能够通过扫描 `brain/` 目录自动完成。
- **对于深度复盘**：在会话结束前，运行上述导出 Prompt，可以获得包含 AI 思考过程（Thinking）和工具调用（Tool Uses）的完美对话记录。
