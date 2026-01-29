# AI Deep Research Agent

一个用于构建「深度研究型 AI Agent」的训练项目，基于 OpenAI 官方 SDK，从零实现 **规划 → 工具调用 → 反思 → 记忆 / 持久化 → 技能扩展** 的完整链路。

---

## 功能特性

- **命令行聊天界面**：启动后即可在终端与 Agent 对话
- **直接调用 OpenAI API**：不依赖 LangChain 等框架，逻辑透明、可定制
- **ReAct 推理 + 工具系统**：
  - `calculator`：安全数学计算
  - `read_doc`：读取 `.doc` / `.docx` 文件
  - `read_file`：读取任意文本文件（`.md`, `.txt`, `.py`, `.json` 等）
  - `pip_install`：在当前环境安装 Python 包
- **规划与反思**：
  - `Planner`：先生成分步计划
  - `ReActAgent`：按计划进行多步工具调用与推理
  - `Reflector`：对回答进行批判性反思与修订
- **记忆与持久化**：
  - `MemoryManager`：对话记忆 + 自动摘要，控制上下文长度
  - Supabase 集成：每轮对话自动写入数据库，便于审计与分析
- **Skills 技能系统**（新增）：
  - 按需加载：启动时只扫描技能名称，调用时才加载内容
  - `/command` 调用：用户通过 `/skill-name [arguments]` 显式调用技能
  - 技能文件支持：自动发现 `resources/`、`scripts/` 等支持文件
  - 变量替换：支持 `$ARGUMENTS`、`${CLAUDE_SESSION_ID}` 等动态变量
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
2. 打开 SQL Editor，执行 `docs/supabase_schema.sql` 中的脚本，创建 `conversations` 表
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
✓ Supabase connection initialized
✓ 发现 1 个技能: contract-review
  使用 /skill-name 调用技能
```

此时可以开始对话：

```text
You: 帮我总结一下强化学习的核心概念
Plan: 1. ... 2. ... 3. ...
Assistant: [按照计划给出回答...]
```

输入 `quit` 或 `exit` 结束会话。

---

## Skills 技能系统

Skills 系统允许你定义可复用的专业技能，通过 `/command` 调用。

### 使用技能

```text
You: /contract-review contracts/example.docx
[skill] 用户调用技能: /contract-review contracts/example.docx
Plan: 1. 读取专家经验文件 2. 读取合同文件 3. 按专家经验审查 4. 输出报告
Assistant: [按照技能定义的流程执行...]
```

### 技能目录结构

```text
skills/
└── contract_review/           # 技能目录（名称即技能名，支持连字符）
    ├── SKILL.md               # 技能定义文件（必需）
    ├── resources/             # 资源文件（可选）
    │   └── expert_experience.md
    └── scripts/               # 辅助脚本（可选）
        └── validate.sh
```

### SKILL.md 格式

```markdown
---
name: contract-review
description: 审查合同文件，识别风险点并提供修改建议。
argument-hint: "[file-path]"
allowed-tools: read_doc, read_file
---

# 合同审查技能

审查 $ARGUMENTS 合同文件...

## 审查流程

1. **读取专家经验文件**：使用 `read_file` 工具读取 `skills/contract_review/resources/expert_experience.md`
2. **读取合同文件**：使用 `read_doc` 工具读取 `$ARGUMENTS`
3. ...
```

### 按需加载机制

- **启动时**：只扫描 `skills/` 目录获取技能名称列表，不读取任何 SKILL.md 内容
- **调用时**：用户输入 `/contract-review` 时才读取并加载对应的 SKILL.md
- **优点**：减少启动时间，节省内存，技能内容不污染普通对话

### 创建新技能

1. 在 `skills/` 下创建新目录（如 `skills/code_review/`）
2. 创建 `SKILL.md` 定义技能
3. 可选：添加 `resources/`、`scripts/` 等支持文件
4. 重启程序，技能自动被发现

---

## 项目结构

```text
deep_research_agent/
├── src/
│   ├── main.py                  # 主入口 & 命令行交互循环
│   ├── llm.py                   # OpenAI LLM 客户端封装
│   ├── agent/                   # Agent 逻辑：规划、ReAct、反思、调度
│   │   ├── orchestrator.py      # AgentOrchestrator，串联所有组件
│   │   ├── planner.py           # Planner，生成分步 Plan
│   │   ├── react_agent.py       # ReActAgent，多步工具调用 + Final
│   │   └── reflection.py        # Reflector，检查并修订回答
│   ├── memory/                  # 对话记忆 & 摘要 & Supabase 持久化
│   │   ├── memory_manager.py    # MemoryManager，控制上下文长度 & 自动摘要
│   │   └── supabase_client.py   # SupabaseClient，对话写入数据库
│   ├── skills/                  # Skills 技能系统
│   │   ├── skill.py             # Skill 数据类
│   │   ├── skill_loader.py      # SkillLoader，按需加载技能
│   │   └── skill_matcher.py     # LazySkillMatcher，匹配 /command
│   ├── tools/                   # 工具系统（ReAct 中可用）
│   │   ├── __init__.py          # Tool / ToolRegistry / 默认工具注册
│   │   └── doc_reader.py        # read_doc 工具：读取 .doc / .docx
│   └── knowledge_base/          # 预留：文档存储 & 检索（RAG 等）
├── skills/                      # 技能定义目录
│   └── contract_review/         # 合同审查技能示例
│       ├── SKILL.md
│       ├── resources/
│       │   └── expert_experience.md
│       └── scripts/
│           └── validate.sh
├── contracts/                   # 测试用合同文件目录
├── docs/
│   ├── SUPABASE_SETUP.md        # Supabase 集成说明
│   └── supabase_schema.sql      # Supabase 表结构 SQL
├── requirements.txt             # Python 依赖
└── README.md                    # 本文件
```

---

## 核心模块说明

### `src/main.py` — 程序入口

- 初始化：
  - `LLMClient`（基于环境变量配置）
  - Supabase 客户端（可选）
  - `MemoryManager`（注入 Supabase 客户端）
  - `SkillLoader` + `LazySkillMatcher`（按需加载技能）
  - 工具注册表 `build_default_tools()`
  - `ReActAgent` / `Reflector` / `AgentOrchestrator`
- 主循环：读取用户输入 → `orchestrator.run()` → 输出结果

### `src/agent/` — Agent 核心逻辑

| 模块 | 功能 |
|------|------|
| `Planner` | 生成分步计划（支持流式输出） |
| `ReActAgent` | ReAct 循环：`Action` → `Observation` → `Final` |
| `Reflector` | 对答案进行反思与修订 |
| `AgentOrchestrator` | 串联所有组件，支持技能上下文注入 |

### `src/skills/` — 技能系统

| 模块 | 功能 |
|------|------|
| `Skill` | 技能数据类，支持变量替换、命令执行 |
| `SkillLoader` | 扫描 `skills/` 目录，按需加载 SKILL.md |
| `LazySkillMatcher` | 匹配 `/command` 调用，只在调用时加载技能内容 |

### `src/tools/` — 工具系统

| 工具 | 功能 |
|------|------|
| `calculator` | 安全数学计算（AST 解析） |
| `read_doc` | 读取 `.doc` / `.docx` 文件 |
| `read_file` | 读取任意文本文件（`.md`, `.txt`, `.py` 等） |
| `pip_install` | 在当前环境执行 `pip install` |

### `src/memory/` — 记忆与持久化

| 模块 | 功能 |
|------|------|
| `MemoryManager` | 对话历史管理，自动摘要，控制上下文长度 |
| `SupabaseClient` | 每轮对话写入 Supabase `conversations` 表 |

---

## 训练与扩展建议

1. **扩展技能**：
   - 创建新技能（代码审查、文档摘要、数据分析等）
   - 为技能添加更多资源文件和专家经验

2. **扩展工具**：
   - Web 搜索 + 页面抓取
   - 代码执行沙箱
   - 数据库查询

3. **记忆升级**：
   - 增加向量记忆（Embeddings）
   - 按主题组织历史对话

4. **知识库（RAG）**：
   - 为 PDF / 网页构建向量索引
   - 将检索到的片段合入上下文

5. **可观察性**：
   - 利用 Supabase 中的对话记录做统计与质量评估
   - 加入反馈和评分字段

---

## 许可证

这是一个用于教学与实验的 Starter Kit，你可以自由地使用、修改和扩展它。
