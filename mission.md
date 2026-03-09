# RetroSpark 项目说明书

## 📌 摘要 (Summary)

本项目旨在构建一个面向 C 端的 AI 应用，用于全面接管、管理并二次开发用户与各类大型语言模型（LLM）的交互信息。系统通过自动化数据抽取、Git 版本控制、多模态内容生成以及 Agent 智能总结，将碎片化的对话记录转化为结构化、可追溯、可复用的个人数字资产。

## ⚙️ 核心功能模块 (Core Features)

1. **全链路数据抽取层 (Data Extraction)**
   * 自动抓取并解析与主流 LLM 的多轮对话历史。
   * 分类提取对话中产生的各类异构资产：纯文本、代码片段、文档草稿、多媒体素材等。
2. **知识版本控制中枢 (Version Control & Storage)**
   * 无缝集成 Git 工作流，对生成的代码和核心文档进行版本追踪。
   * 自动提交 (Auto-commit) 至指定的 GitHub 仓库进行长期沉淀与维护。
3. **Agent 自动化调度与总结 (Automated Agentic Summarization)**
   * 引入 LLM Agent 进行项目管理和日常工作复盘。
   * 按日/按阶段自动生成工作简报，将发散的对话收敛为清晰的执行结论。
4. **多模态输入/输出引擎 (Multimodal I/O)**
   * **输入**：支持便捷的语音录入与意图识别。
   * **输出**：
     * **音频流**：将核心笔记转化为语音或播客形态。
     * **视觉化**：自动生成信息图谱、思维导图 (Mind maps)，梳理知识脉络。
     * **文本流**：输出适配 Obsidian、Notion 等知识管理软件的结构化 Markdown 文档或笔记。

## 🏗️ 架构与技术实现路径 (Architecture & Implementation)

基于当前的技术栈生态，本系统的实现可以采用以下路径：

* **后端引擎**：采用 Python 编写核心逻辑，利用其强大的文本处理能力和成熟的 AI 库。
* **自动化与容器化**：依托 GitHub Actions 进行工作流的自动化运转，并通过 Docker 实现快速部署与隔离运行。
* **开发参考**：需进一步调研 Cloud Code 平台（或 GitHub）上已有的开源项目，借鉴其 API 桥接与数据解析策略。

## 🧠 深度分析与思考 (In-depth Analysis & Provoking Thoughts)

* **数据流动性与知识复利**：用户每天花费数小时阅读学术文献 并与 LLM 交互，这些过程中产生了大量极具价值的“中间态”知识（如 Prompt 迭代记录、代码 Debug 过程）。目前的痛点在于这些知识被封闭在各个平台的聊天窗口中。本产品的核心价值在于**打破信息孤岛**，使知识具备流动性和复利效应。
* **从工具到副脑 (From Tool to Exocortex)**：通过让 LLM 充当产品设计与代码实现 Agent，这套系统不仅仅是一个“备份工具”，而是一个能够自我反思和梳理的“数字副脑”。系统定期生成的结构化笔记，甚至可以直接作为素材，无缝输出到您的个人博客“My Odyssey Towards AI”中。
* **隐私与数据主权 (Privacy & Data Sovereignty)**：由于涉及个人的思考痕迹与核心代码，系统必须高度重视数据隐私。采用本地优先 (Local-first) 结合私有 GitHub 仓库的混合架构，是保障数字资产安全的必要设计。

## ✅ 最小化产品 (MVP)

最小化产品首先聚焦在 Vibe Coding 辅助编程工具（如 Google Antigravity, Claude Code, Codex, Gemini CLI, OpenCode, OpenClaw, and Kimi）等，旨在全面管理用户与辅助编程工具的交互数据。

最小化产品包括的功能有：  

* 全链路数据抽取层 (Data Extraction)
* 知识版本控制中枢 (Version Control & Storage)

以下功能为进一步的增强功能：  

* Agent 自动化调度与总结 (Automated Agentic Summarization)

再接下来的增值功能有：  

* 多模态输入/输出引擎 (Multimodal I/O)

最小化产品将开发为 [agent skills](https://agentskills.io/home)的形态，以方便在上述Vibe Coding 辅助编程工具中使用。其具体实现应当参考 [DataClaw](https://github.com/peteromallet/dataclaw/)项目，项目代码和功能参考DataClaw，避免重复造轮子。
