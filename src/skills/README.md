# Skills 模块

技能（Skills）扩展了 Agent 的能力。遵循 [Claude Code Agent Skills](https://agentskills.io) 开放标准。

## 创建技能

1. 在 `skills/` 目录下创建技能目录
2. 编写 `SKILL.md` 文件，包含 YAML frontmatter 和 markdown 内容

### 目录结构

```
skills/
└── my-skill/
    ├── SKILL.md           # 主要说明（必需）
    ├── resources/         # 参考资料
    │   └── reference.md
    ├── examples/          # 示例
    │   └── sample.md
    ├── scripts/           # 可执行脚本
    │   └── helper.sh
    └── templates/         # 模板文件
        └── output.md
```

### SKILL.md 格式

```yaml
---
name: my-skill                    # 技能名称，用于 /slash-command
description: 技能描述              # 帮助 Claude 决定何时使用
argument-hint: "[file-path]"      # 参数提示
disable-model-invocation: false   # true = 只有用户可以调用
user-invocable: true              # false = 只有 Claude 可以调用
allowed-tools: Read, Grep         # 允许的工具
context: fork                     # "fork" = 在子代理中运行
agent: Explore                    # 子代理类型
---

# 技能标题

技能的 markdown 内容...
```

## Frontmatter 字段

| 字段 | 必需 | 描述 |
|------|------|------|
| `name` | 否 | 技能名称，默认使用目录名 |
| `description` | 推荐 | 技能描述，Claude 用于决定何时使用 |
| `argument-hint` | 否 | 参数提示，如 `[file-path]` |
| `disable-model-invocation` | 否 | `true` = 禁止 Claude 自动调用 |
| `user-invocable` | 否 | `false` = 从用户菜单隐藏 |
| `allowed-tools` | 否 | 允许使用的工具列表 |
| `context` | 否 | `fork` = 在子代理中运行 |
| `agent` | 否 | 子代理类型 |

## 变量替换

| 变量 | 描述 |
|------|------|
| `$ARGUMENTS` | 用户传递的参数 |
| `${CLAUDE_SESSION_ID}` | 当前会话 ID |

## 动态上下文

使用 `` !`command` `` 语法在技能加载时执行命令：

```markdown
当前目录文件: !`ls -la`
Git 状态: !`git status --short`
```

## 调用控制

| 配置 | 用户可调用 | Claude 可调用 |
|------|-----------|--------------|
| 默认 | ✓ | ✓ |
| `disable-model-invocation: true` | ✓ | ✗ |
| `user-invocable: false` | ✗ | ✓ |

## 使用示例

### 用户显式调用

```
/contract-review contracts/example.docx
```

### Claude 自动调用

当用户输入匹配技能描述时，Claude 会自动加载技能。

## API

```python
from skills import SkillLoader, LLMSkillMatcher

# 加载技能
loader = SkillLoader("skills/")
skills = loader.load_all()

# 创建匹配器
matcher = LLMSkillMatcher(llm, skills)

# 用户命令匹配
result = matcher.match_user_command("/contract-review file.docx")
if result:
    skill, arguments = result

# Claude 自动匹配
skill = matcher.match_for_model("帮我审查这份合同")
```
