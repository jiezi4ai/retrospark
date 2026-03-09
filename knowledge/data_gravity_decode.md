# Antigravity 交互数据解码与解析指南

Google Antigravity 是一款由 Google 推出的“Agent-first” AI 编程 IDE（基于 VS Code 深度定制）。它的交互数据（如对话历史、Agent 生成的 Artifacts、知识库等）主要**存储在本地文件系统中**，而不是完全依赖云端。

### 一、 交互数据存放在哪里？

根据不同操作系统，Antigravity 的核心交互数据主要存放在用户主目录下的 `.gemini/antigravity/` 和 `.config/Antigravity/` (或 `.antigravity-server/`) 文件夹中：

1. **对话历史 (Chat History) 与 Agent 状态**
   * **路径**：`~/.gemini/antigravity/conversations/` （Windows 下为 `C:\Users\<用户名>\.gemini\antigravity\conversations\`）
   * **格式**：这些文件以 UUID 命名，并且是**加密的二进制 Protocol Buffers (`.pb`) 格式**。
   * **特征**：具有极高的熵值（~0.97），密钥由系统级 Secret Storage 管理。

2. **全局大脑与知识库 (Brain / Knowledge / Artifacts)**
   * **路径**：`~/.gemini/antigravity/brain/` 或 `~/.gemini/antigravity/knowledge/`
   * **内容**：存放 Agent 生成的 Artifacts（如 `task.md`, `implementation_plan.md`, `walkthrough.md`），且为**全明文 Markdown 格式**。

3. **临时会话 (Scratch / Playground)**
   * **路径**：`~/.gemini/antigravity/scratch/` 或 `~/.gemini/antigravity/playground/`
   * **内容**：未绑定特定本地工作区的全局对话数据。

4. **IDE 全局与工作区状态 (继承自 VS Code)**
   * **路径**：`~/.config/Antigravity/User/globalStorage/state.vscdb` 或 `~/.antigravity-server/data/User/globalStorage/state.vscdb`
   * **格式**：标准的 **SQLite 数据库**，包含对话索引和元数据。

---

### 二、 数据解析方案：从加密到明文的转变 (2026-03-08 实机探测更新)

#### 1. `.pb` 文件的加密屏障 (对话原始日志)

* **现状**：虽然名为 Protobuf，但文件已加密。传统的 `protoc --decode_raw` 或 `blackboxprotobuf` 无法直接解码密文。
* **结论**：直接同步 `.pb` 文件在当前外部工具（如 RetroSpark）中不可行，除非能获取解密密钥。

* **绕行方案**: 社区开发者发现了一个巧妙的绕过二进制解析的方法：**直接让 Antigravity 的 AI 帮你导出**。

1. 在 Antigravity 中新建一个对话。
2. 向 Agent 发送类似如下的 Prompt：
   > "Please use your `list_dir` and file reading tools to access `~/.gemini/antigravity/conversations/`. Find the most recent conversation file, read its contents (or the corresponding artifacts in the `brain` folder), and summarize our entire chat history. Finally, export this history into a well-formatted `.json` file in my current workspace."
3. Agent 会利用其内置的系统权限读取并理解这些文件，然后直接在你的项目目录中生成一个 `.json` 格式的对话记录。

#### 2. `brain/` 目录：明文解析的“金矿” (推荐方案)

这是目前解析 Antigravity 交互最可靠、最高效的途径：

* **路径**：`~/.gemini/antigravity/brain/<Session-UUID>/`
* **实测文件结构**：
  * `task.md` / `task.md.resolved.[N]`：任务进度与决策历史，支持版本回溯。
  * `implementation_plan.md`：详细技术实施方案。
  * `*.metadata.json`：包含 `artifactType`, `summary`, `updatedAt` 等关键元数据，便于第三方工具建立索引。
* **优势**：全明文、高结构化、带有版本快照。

#### 3. 辅助元数据提取

如果需要关联对话名称或工作区，可以检索 Windows 侧的 `state.vscdb`：

* **路径分布**：
  * **标准桌面版**: `~/.config/Antigravity/User/globalStorage/state.vscdb`
  * **Server/WSL版**: 数据可能迁移至 `~/.antigravity-server/data/User/`。
* **关键发现**：在某些 Server 构建版中，`state.vscdb` 可能不以独立 SQLite 文件形式存在，或者采用了内存映射/专用服务端同步机制。建议在集成时先探测 `globalStorage` 目录下的文件特征。

---

### 三、 总结与建议

对于 RetroSpark 等第三方工具，建议优先扫描 `brain/` 目录下的 Markdown 文件。这种方式不仅避开了加密难题，还能获得比原始对话更具语义化和结构化的交互摘要。
