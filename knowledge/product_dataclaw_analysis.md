# DataClaw 调研

DataClaw是一个非常贴近本项目的前沿参考项目。虽然 DataClaw 的最终目的是将数据发布到 Hugging Face 构建开源数据集，但它在**数据抽取、结构化解析、隐私脱敏以及面向 Agent 的工程设计**上，完美实现了您构想中的“前半程”工作。

以下是对 [DataClaw](https://github.com/peteromallet/dataclaw/tree/main) 源码的深度分析，以及它如何反哺您“个人知识库与二次开发”的想法：

### A. 核心功能与特色分析 (Features & Characteristics)

**1. 多源异构数据的统一抽取 (Multi-source Extraction)**

DataClaw 并不是通过 API 拦截，而是直接去用户的本地隐藏文件夹中“挖坟”。它支持解析市面上几乎所有主流的 CLI 编程智能体产生的对话记录，包括 Claude Code (`~/.claude`)、Codex (`~/.codex`)、Gemini CLI (`~/.gemini/tmp`)、OpenCode (读取 SQLite 数据库 `opencode.db`)、OpenClaw 以及 Kimi。

- **特色**：它将这些不同平台、不同格式的底层日志统一转换为了标准化的 JSON Schema，其中包含了用户消息、AI 回复、大模型的深度思考过程（thinking）、工具调用记录（tool_uses，含输入输出）以及消耗的 Token 统计。

**2. 极度严格的多层隐私脱敏 (Deep Privacy & Redaction)**

由于涉及个人的核心代码和对话，DataClaw 在隐私保护上做得非常极致：

- **路径与身份匿名化**：将绝对路径（如 `/Users/name/project`）截断为相对于项目的路径，并将 macOS 的用户名通过 SHA-256 哈希处理（如 `user_a1b2c3d4`）。
- **正则与高熵字符串扫描**：不仅使用正则匹配 JWT、API Keys、IP 地址和邮箱，还专门实现了一个 `_scan_high_entropy_strings` 函数，通过计算香农熵（Shannon entropy > 4.0）来抓取那些伪装成普通文本但实际上可能是密码或密钥的高熵随机字符串。

**3. 面向 Agent 编程的原生设计 (Agent-Native Design)**

这是 DataClaw 最具启发性的一点。它不仅是一个供人类使用的 CLI 工具，更是**专门写给 AI Agent 用的工具**。

- **特色**：当运行 `dataclaw prep` 或 `dataclaw status` 时，它输出的不是人类友好的文本，而是**纯 JSON**，并在其中明确包含 `next_steps`（下一步指南）和 `next_command`（下一步指令）。开发者只需将 `AGENTS.md` 中的系统提示词喂给大模型，大模型就能全自动地阅读 JSON、执行命令、完成从分析到导出的全流程。

**4. 强制的安全审计工作流 (Mandatory Guardrails)**

系统具有强状态机特性（分为 auth, configure, review, confirmed, done 阶段）。

- **特色**：它强制要求先导出到本地（`--no-push`），并要求大模型询问用户的全名进行精准过滤。在没有获得用户明确的文本确认（Attestation）之前，系统会锁死推送功能，拒绝上传。

### B. 底层技术实现逻辑 (Implementation Details)

- **数据读取层 (`parser.py`)**：大量使用了 Python 的 `Pathlib` 和 `json.loads` 去逐行读取本地隐藏目录下的 `.jsonl` 文件。针对 OpenCode 这种使用 SQLite 的平台，则利用内置的 `sqlite3` 库执行 SQL 联表查询（将 `session`, `message`, `part` 表关联组合）提取对话上下文。
- **脱敏层 (`anonymizer.py`)**：通过维护一个包含用户真实名字和各种组合路径的映射表（正则表达式），在内存中对所有提取出的字符串和文件路径执行实时的无状态替换。
- **发布层 (`cli.py`)**：集成了 `huggingface_hub`，在内存中动态生成包含各种元数据（Token消耗、模型占比、时间戳）的 `README.md` (Dataset Card)，并通过 API 将最终的 `conversations.jsonl` 一键推送到云端。
