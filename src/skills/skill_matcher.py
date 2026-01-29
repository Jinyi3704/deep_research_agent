from __future__ import annotations

import re
from typing import List, Optional

from skills.skill import Skill


class SkillMatcher:
    """
    技能匹配器 - 根据用户输入匹配最合适的技能。
    
    支持两种调用方式：
    1. 用户显式调用: /skill-name [arguments]
    2. Claude 自动调用: 根据 description 语义匹配
    """

    def __init__(self, skills: List[Skill]) -> None:
        self.skills = skills
        self._skill_map = {s.name: s for s in skills}

    def match_user_command(self, user_input: str) -> Optional[tuple[Skill, str]]:
        """
        匹配用户显式调用的 /skill-name 命令。
        
        Returns:
            (skill, arguments) 或 None
        """
        if not user_input.startswith("/"):
            return None
        
        # 解析 /command [arguments]
        parts = user_input[1:].split(maxsplit=1)
        if not parts:
            return None
        
        command_name = parts[0].lower()
        arguments = parts[1] if len(parts) > 1 else ""
        
        # 查找匹配的技能
        skill = self._skill_map.get(command_name)
        if skill and skill.can_user_invoke():
            return skill, arguments
        
        # 尝试模糊匹配（用连字符替换空格）
        for name, skill in self._skill_map.items():
            if name.replace("-", " ") == command_name.replace("-", " "):
                if skill.can_user_invoke():
                    return skill, arguments
        
        return None

    def match_for_model(self, user_input: str) -> Optional[Skill]:
        """
        为 Claude 自动调用匹配技能（基于 description 语义）。
        
        只返回 can_model_invoke() == True 的技能。
        """
        user_input_lower = user_input.lower()
        
        for skill in self.skills:
            if not skill.can_model_invoke():
                continue
            
            keywords = self._extract_keywords(skill.description)
            for kw in keywords:
                if kw in user_input_lower:
                    return skill
        
        return None

    def _extract_keywords(self, description: str) -> List[str]:
        """从 description 提取关键词"""
        keywords = []
        
        # 匹配中文引号、英文引号内的内容
        matches = re.findall(r'[""\'「」『』]([^""\'「」『』]+)[""\'「」『』]', description)
        keywords.extend([m.strip().lower() for m in matches if m.strip()])
        
        # 匹配 "包含xxx、yyy、zzz时" 模式
        pattern = r"包含[：:\"\"\']*([^时]+)[时]?"
        match = re.search(pattern, description)
        if match:
            parts = re.split(r"[、，,]", match.group(1))
            keywords.extend([p.strip().lower() for p in parts if p.strip()])
        
        # 匹配 "Use when..." 模式
        use_when = re.search(r"Use when\s+(.+?)(?:\.|$)", description, re.IGNORECASE)
        if use_when:
            keywords.append(use_when.group(1).strip().lower())
        
        return keywords

    def get_available_commands(self) -> List[str]:
        """获取所有可用的 /command 列表"""
        return [f"/{s.name}" for s in self.skills if s.can_user_invoke()]

    def get_skill_descriptions(self) -> str:
        """获取所有 Claude 可调用技能的描述（用于注入上下文）"""
        lines = []
        for skill in self.skills:
            if skill.can_model_invoke():
                hint = f" {skill.argument_hint}" if skill.argument_hint else ""
                lines.append(f"- /{skill.name}{hint}: {skill.description}")
        return "\n".join(lines)


class LLMSkillMatcher:
    """
    使用 LLM 进行语义匹配的技能匹配器（更智能）。
    
    只匹配 can_model_invoke() == True 的技能。
    """

    def __init__(self, llm, skills: List[Skill]) -> None:
        self.llm = llm
        self.skills = skills
        self._skill_map = {s.name: s for s in skills}
        # 过滤出 Claude 可以调用的技能
        self._model_invocable = [s for s in skills if s.can_model_invoke()]

    def match_user_command(self, user_input: str) -> Optional[tuple[Skill, str]]:
        """匹配用户显式调用的 /skill-name 命令"""
        if not user_input.startswith("/"):
            return None
        
        parts = user_input[1:].split(maxsplit=1)
        if not parts:
            return None
        
        command_name = parts[0].lower()
        arguments = parts[1] if len(parts) > 1 else ""
        
        skill = self._skill_map.get(command_name)
        if skill and skill.can_user_invoke():
            return skill, arguments
        
        return None

    def match_for_model(self, user_input: str) -> Optional[Skill]:
        """使用 LLM 为 Claude 自动调用匹配技能"""
        if not self._model_invocable:
            return None

        skill_list = "\n".join([
            f"- {s.name}: {s.description}" for s in self._model_invocable
        ])

        prompt = f"""根据用户输入，判断应该使用哪个技能。如果没有匹配的技能，返回 "none"。

可用技能：
{skill_list}

用户输入：{user_input}

只返回技能名称（如 "fix-issue"）或 "none"，不要返回其他内容。"""

        messages = [{"role": "user", "content": prompt}]
        result = (self.llm.chat(messages, stream=False) or "").strip().lower()

        for skill in self._model_invocable:
            if skill.name.lower() == result:
                return skill
        return None

    def get_available_commands(self) -> List[str]:
        """获取所有可用的 /command 列表"""
        return [f"/{s.name}" for s in self.skills if s.can_user_invoke()]

    def get_skill_descriptions(self) -> str:
        """获取所有 Claude 可调用技能的描述"""
        lines = []
        for skill in self._model_invocable:
            hint = f" {skill.argument_hint}" if skill.argument_hint else ""
            lines.append(f"- /{skill.name}{hint}: {skill.description}")
        return "\n".join(lines)
