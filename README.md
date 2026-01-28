# AI Deep Research Agent

一个用于构建「深度研究型 AI Agent」的训练项目，基于 OpenAI 官方 SDK，从零实现 **规划 → 工具调用 → 反思 → 记忆 / 持久化** 的完整链路。

---

## 功能特性

- **命令行聊天界面**：启动后即可在终端与 Agent 对话
- **直接调用 OpenAI API**：不依赖 LangChain 等框架，逻辑透明、可定制
- **ReAct 推理 + 工具系统**：
  - `calculator`：安全数学计算
  - `read_doc`：读取 `.doc` / `.docx` 文件
  - `pip_install`：在当前环境安装 Python 包
- **规划与反思**：
  - `Planner`：先生成分步计划
  - `ReActAgent`：按计划进行多步工具调用与推理
  - `Reflector`：对回答进行批判性反思与修订
- **记忆与持久化**：
  - `MemoryManager`：对话记忆 + 自动摘要，控制上下文长度
  - Supabase 集成：每轮对话自动写入数据库，便于审计与分析
- **流式输出与调试开关**：支持规划流式、回答流式、工具日志、反思日志等

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：

- `openai`：官方 Python SDK
- `python-dotenv`：加载 `.env` 配置
- `supabase`：Supabase 客户端（对话持久化）
- `python-docx`：解析 `.docx` 文档

### 2. 配置环境变量

创建并编辑 `.env`（你也可以基于 `.env.example` 创建）：

```env
# OpenAI / 兼容 API
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini

# 可选：Supabase 对话持久化
SUPABASE_URL=your_supabase_url
SUPABASE_API_KEY=your_supabase_api_key
```

> **说明**：如果不配置 Supabase，程序仍能运行，只是不会把对话写入数据库。

### 3. 配置 Supabase（可选但推荐）

1. 在 Supabase 控制台新建或使用现有项目  
2. 打开 SQL Editor，执行 `docs/supabase_schema.sql` 中的脚本，创建 `conversations` 表：包含 `user_input`、`assistant_output`、`plan`、`reflection`、`session_id`、`created_at` 等字段  
3. 在 `.env` 中填入 `SUPABASE_URL` 和 `SUPABASE_API_KEY`

> 详细说明见 `docs/SUPABASE_SETUP.md`。

### 4. 运行应用

```bash
cd src
python main.py
```

终端中会看到类似输出：

```text
AI Deep Research Agent - Starter Kit
==================================================
Type 'quit' or 'exit' to end the conversation
==================================================
```

此时可以开始对话：

```text
You: 帮我总结一下强化学习的核心概念
Plan: 1. ... 2. ... 3. ...
Assistant: [按照计划、可能结合工具给出回答...]
```

输入 `quit` 或 `exit` 结束会话。

---

## 项目结构

```text
deep_research_agent/
├── src/
│   ├── __init__.py
│   ├── main.py              # 主入口 & 命令行交互循环
│   ├── llm.py               # OpenAI LLM 客户端封装
│   ├── agent/               # Agent 逻辑：规划、ReAct、反思、调度
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # AgentOrchestrator，串联 Planner / ReAct / Reflector / Memory
│   │   ├── planner.py       # Planner，生成分步 Plan
│   │   ├── react_agent.py   # ReActAgent，多步工具调用 + Final
│   │   └── reflection.py    # Reflector，检查并修订回答
│   ├── memory/              # 对话记忆 & 摘要 & Supabase 持久化
│   │   ├── __init__.py
│   │   ├── memory_manager.py    # MemoryManager，控制上下文长度 & 自动摘要
│   │   └── supabase_client.py   # SupabaseClient，对话写入数据库
│   ├── knowledge_base/      # 预留：文档存储 & 检索（RAG 等）
│   │   ├── __init__.py
│   │   └── README.md
│   └── tools/               # 工具系统（ReAct 中可用）
│       ├── __init__.py      # Tool / ToolRegistry / 默认工具注册
│       ├── doc_reader.py    # read_doc 工具：读取 .doc / .docx
│       └── README.md
├── docs/
│   ├── SUPABASE_SETUP.md    # Supabase 集成 & 使用说明
│   └── supabase_schema.sql  # Supabase 表结构 SQL
├── requirements.txt         # Python 依赖
├── .env.example             # 示例环境配置
├── .env                     # 实际环境变量（已 gitignore）
├── .gitignore               # Git 忽略规则
└── README.md                # 本文件
```

---

## 核心模块说明

### `src/main.py` — 程序入口 & 交互循环

- 初始化：
  - `LLMClient`（基于 `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`MODEL`）
  - Supabase 客户端（如果环境配置可用）
  - `MemoryManager`（注入 Supabase 客户端，用于持久化）
  - 工具注册表 `build_default_tools()`
  - `ReActAgent` / `Reflector` / `AgentOrchestrator`
- 主循环：
  - 读取用户输入
  - 调用 `orchestrator.run(...)` 获取回答
  - 根据配置决定是否展示 **计划**、**工具日志**、**反思日志**、**流式输出**

### `src/llm.py` — LLM 客户端封装

- 使用 `openai` 官方 SDK：
  - 初始化 `OpenAI` 客户端
  - 提供 `chat(messages, model=None, stream=True)`：
    - `stream=True`：返回流式迭代器（用于边生成边打印）
    - `stream=False`：返回完整字符串结果

### `src/agent/` — Planner / ReAct / Reflector / Orchestrator

- `Planner`：
  - 输入：用户请求 + 当前上下文
  - 输出：**最多 N 步的编号计划**（1., 2., 3. ...）
  - 可选流式输出（在终端先打印 Plan）
- `ReActAgent`：
  - System Prompt 中列出所有工具（名称、描述、参数）
  - 协议：
    - 调用工具：  
      `Action: <tool_name>`  
      `Action Input: <json>`
    - 最终答案：  
      `Final: <answer>`
  - 解析工具调用 → 执行 → 将 `Observation: ...` 反馈给模型 → 直到产生 `Final:`
  - 支持流式输出 `Final:` 之后的内容
- `Reflector`：
  - 对草稿答案从 **准确性 / 完整性 / 清晰度** 维度进行反思
  - 输出：  
    `Reflection: <简短评语>`  
    `Final: <可能修订后的答案>`
- `AgentOrchestrator`：
  - 串联：`MemoryManager` → `Planner` → `ReActAgent` → `Reflector` → `MemoryManager`
  - 记录 `last_plan` / `last_reflection`，供 UI 打印

### `src/memory/` — MemoryManager & Supabase 持久化

- `MemoryManager`：
  - 维护内存中的消息列表 `messages`
  - 按需生成和维护一个简要 `summary`，避免上下文过长
  - `get_context()`：
    - 若有 summary：先注入一条 `system` 消息包含摘要
    - 再附上最近 `max_messages` 条消息
  - 当消息数超过 `summary_trigger` 时：
    - 使用 LLM 对较早消息进行摘要
    - 只保留最近 `summary_keep` 条详细消息
- `SupabaseClient`：
  - `save_conversation(user_input, assistant_output, plan, reflection, session_id)`：
    - 将每一轮对话写入 Supabase 的 `conversations` 表
    - 若失败，仅打印错误，不影响对话主流程

### `src/tools/` — 工具系统

#### `ToolRegistry` & 默认工具

- `Tool`：包含 `name` / `description` / `parameters`（JSON Schema 风格）/ `func`
- `ToolRegistry`：注册、查询、枚举工具
- `build_default_tools()` 当前注册：
  - `calculator`：
    - 使用安全的 AST 解析仅支持四则运算、幂、取模等
  - `read_doc`：
    - 读取 `.docx`：使用 `python-docx`
    - 读取 `.doc`：尝试调用系统 `antiword`（需本地安装），否则返回提示
    - 支持 `max_chars` 截断长文档
  - `pip_install`：
    - 在当前环境执行 `pip install <package>`
    - 返回 stdout / stderr，方便在终端检查结果

> 提示：你可以在 `tools/` 下继续扩展：Web 搜索、爬虫、代码执行、文件系统操作等。

---

## 训练与扩展建议

这个项目的目标是让你从「调用 LLM」走向「构建一个可用的研究 Agent」。可以按以下路线扩展：

1. **记忆模块升级**：
   - 增加长期向量记忆（向量库 / Embeddings）
   - 按主题 / 任务维度组织历史对话
2. **工具系统扩展**：
   - Web 搜索 + 抓取页面内容
   - 结构化数据查询（SQL / API）
   - 代码执行沙箱
3. **知识库（RAG）**：
   - 为 PDF / 网页构建向量索引
   - 将检索到的片段合入上下文
4. **多轮研究流程**：
   - 支持「研究任务」模式：分解任务 → 查询资料 → 生成中间笔记 → 汇总报告
5. **可观察性与评估**：
   - 利用 Supabase 中的对话记录做统计与质量评估
   - 加入简单的评分或反馈字段（如人工打分）

---

## 许可证

这是一个用于教学与实验的 Starter Kit，你可以自由地使用、修改和扩展它，以适配自己的训练或项目需求。
