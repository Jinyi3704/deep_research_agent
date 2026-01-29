from __future__ import annotations

import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Skill:
    """
    表示一个技能，遵循 Claude Code Agent Skills 标准。
    
    参考: https://code.claude.com/docs/skills
    """

    # 必需
    path: str  # skill 目录路径

    # 核心字段
    name: str = ""  # 技能名称，用于 /slash-command
    description: str = ""  # 描述，帮助 Claude 决定何时使用
    content: str = ""  # SKILL.md 的 markdown 内容（frontmatter 之后的部分）

    # 可选配置
    argument_hint: str = ""  # 参数提示，如 "[issue-number]"
    disable_model_invocation: bool = False  # True = 只有用户可以调用
    user_invocable: bool = True  # False = 只有 Claude 可以调用（从菜单隐藏）
    allowed_tools: List[str] = field(default_factory=list)  # 允许的工具列表
    model: str = ""  # 指定使用的模型
    context: str = ""  # "fork" = 在子代理中运行
    agent: str = ""  # 子代理类型 (Explore, Plan, general-purpose)

    # 支持文件
    supporting_files: Dict[str, str] = field(default_factory=dict)  # 文件名 -> 相对路径

    def get_content_with_substitutions(
        self,
        arguments: str = "",
        session_id: Optional[str] = None,
        execute_commands: bool = True,
    ) -> str:
        """
        获取处理过变量替换后的技能内容。
        
        支持:
        - $ARGUMENTS: 用户传递的参数
        - ${CLAUDE_SESSION_ID}: 当前会话 ID
        - !`command`: 动态执行命令并替换输出
        """
        content = self.content
        
        # 替换 $ARGUMENTS
        if "$ARGUMENTS" in content:
            content = content.replace("$ARGUMENTS", arguments)
        elif arguments:
            # 如果内容中没有 $ARGUMENTS，追加到末尾
            content += f"\n\nARGUMENTS: {arguments}"
        
        # 替换 ${CLAUDE_SESSION_ID}
        sid = session_id or str(uuid.uuid4())
        content = content.replace("${CLAUDE_SESSION_ID}", sid)
        
        # 执行 !`command` 并替换
        if execute_commands:
            content = self._execute_inline_commands(content)
        
        return content

    def _execute_inline_commands(self, content: str) -> str:
        """执行 !`command` 语法的命令并替换输出"""
        pattern = r"!\`([^`]+)\`"
        
        def replace_command(match):
            cmd = match.group(1)
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.path,
                )
                return result.stdout.strip() if result.returncode == 0 else f"[Command failed: {result.stderr.strip()}]"
            except subprocess.TimeoutExpired:
                return "[Command timeout]"
            except Exception as e:
                return f"[Command error: {e}]"
        
        return re.sub(pattern, replace_command, content)

    def get_system_prompt_addition(self, arguments: str = "", session_id: Optional[str] = None) -> str:
        """返回要注入到 system prompt 中的内容"""
        content = self.get_content_with_substitutions(arguments, session_id)
        if not content:
            return ""
        return f"\n\n## 技能: {self.name}\n{content}"

    def get_supporting_file_content(self, filename: str) -> Optional[str]:
        """读取支持文件的内容"""
        if filename not in self.supporting_files:
            return None
        filepath = os.path.join(self.path, self.supporting_files[filename])
        if not os.path.isfile(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def can_model_invoke(self) -> bool:
        """Claude 是否可以自动调用此技能"""
        return not self.disable_model_invocation

    def can_user_invoke(self) -> bool:
        """用户是否可以通过 /command 调用此技能"""
        return self.user_invocable

    def should_fork_context(self) -> bool:
        """是否应该在子代理中运行"""
        return self.context == "fork"
