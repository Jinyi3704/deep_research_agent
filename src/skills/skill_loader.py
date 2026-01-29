from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from skills.skill import Skill


def _parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    解析 YAML frontmatter 和 markdown 内容。
    
    Returns:
        (frontmatter_dict, markdown_content)
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if not match:
        return {}, content.strip()
    
    frontmatter_text = match.group(1)
    markdown_content = content[match.end():].strip()
    
    # 简单的 YAML 解析（支持基本类型）
    frontmatter: Dict[str, Any] = {}
    current_key = None
    
    for line in frontmatter_text.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        
        # 检查是否是 key: value 格式
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            
            # 处理布尔值
            if value.lower() in ("true", "yes"):
                frontmatter[key] = True
            elif value.lower() in ("false", "no"):
                frontmatter[key] = False
            # 处理列表（单行逗号分隔）
            elif "," in value:
                frontmatter[key] = [v.strip() for v in value.split(",") if v.strip()]
            # 处理空值（可能是多行列表的开始）
            elif not value:
                frontmatter[key] = []
                current_key = key
            else:
                # 去掉引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                frontmatter[key] = value
        # 处理多行列表项
        elif line.strip().startswith("-") and current_key:
            item = line.strip()[1:].strip()
            if isinstance(frontmatter.get(current_key), list):
                frontmatter[current_key].append(item)
    
    return frontmatter, markdown_content


class SkillLoader:
    """
    从 skills 目录加载所有技能定义。
    
    遵循 Claude Code Agent Skills 标准:
    - skills/<skill-name>/SKILL.md
    - 支持 scripts/, examples/, templates/ 等子目录
    """

    def __init__(self, skills_dir: str) -> None:
        self.skills_dir = skills_dir
        self._skills: Dict[str, Skill] = {}

    def load_all(self) -> List[Skill]:
        """加载 skills_dir 下所有技能"""
        if not os.path.isdir(self.skills_dir):
            return []

        skills = []
        for name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, name)
            if not os.path.isdir(skill_path):
                continue
            # 跳过隐藏目录
            if name.startswith("."):
                continue

            skill = self._load_skill(skill_path, name)
            if skill:
                skills.append(skill)
                self._skills[skill.name] = skill

        return skills

    def _load_skill(self, skill_path: str, dir_name: str) -> Optional[Skill]:
        """加载单个技能"""
        skill_md = os.path.join(skill_path, "SKILL.md")
        if not os.path.isfile(skill_md):
            return None

        with open(skill_md, "r", encoding="utf-8") as f:
            raw_content = f.read()

        frontmatter, markdown_content = _parse_frontmatter(raw_content)
        
        # 获取基本字段
        name = frontmatter.get("name", dir_name)
        description = frontmatter.get("description", "")
        
        # 如果没有 description，使用 markdown 内容的第一段
        if not description and markdown_content:
            first_para = markdown_content.split("\n\n")[0]
            # 去掉 markdown 标题
            if first_para.startswith("#"):
                lines = markdown_content.split("\n")
                for i, line in enumerate(lines):
                    if not line.startswith("#") and line.strip():
                        description = line.strip()
                        break
            else:
                description = first_para.strip()
        
        # 解析 allowed-tools（支持逗号分隔或列表）
        allowed_tools = frontmatter.get("allowed-tools", [])
        if isinstance(allowed_tools, str):
            allowed_tools = [t.strip() for t in allowed_tools.split(",") if t.strip()]
        
        # 发现支持文件
        supporting_files = self._discover_supporting_files(skill_path)

        return Skill(
            path=skill_path,
            name=name,
            description=description,
            content=markdown_content,
            argument_hint=frontmatter.get("argument-hint", ""),
            disable_model_invocation=frontmatter.get("disable-model-invocation", False),
            user_invocable=frontmatter.get("user-invocable", True),
            allowed_tools=allowed_tools,
            model=frontmatter.get("model", ""),
            context=frontmatter.get("context", ""),
            agent=frontmatter.get("agent", ""),
            supporting_files=supporting_files,
        )

    def _discover_supporting_files(self, skill_path: str) -> Dict[str, str]:
        """发现技能目录中的支持文件"""
        supporting_files: Dict[str, str] = {}
        
        # 支持的子目录
        subdirs = ["scripts", "examples", "templates", "resources"]
        
        for subdir in subdirs:
            subdir_path = os.path.join(skill_path, subdir)
            if os.path.isdir(subdir_path):
                for filename in os.listdir(subdir_path):
                    filepath = os.path.join(subdir_path, filename)
                    if os.path.isfile(filepath):
                        key = f"{subdir}/{filename}"
                        supporting_files[key] = os.path.join(subdir, filename)
        
        # 根目录的支持文件（排除 SKILL.md）
        for filename in os.listdir(skill_path):
            filepath = os.path.join(skill_path, filename)
            if os.path.isfile(filepath) and filename != "SKILL.md":
                supporting_files[filename] = filename
        
        return supporting_files

    def get(self, name: str) -> Optional[Skill]:
        """按名称获取技能"""
        return self._skills.get(name)

    def list(self) -> List[Skill]:
        """列出所有已加载的技能"""
        return list(self._skills.values())

    def names(self) -> List[str]:
        """列出所有技能名称"""
        return sorted(self._skills.keys())

    def get_model_invocable_skills(self) -> List[Skill]:
        """获取 Claude 可以自动调用的技能"""
        return [s for s in self._skills.values() if s.can_model_invoke()]

    def get_user_invocable_skills(self) -> List[Skill]:
        """获取用户可以调用的技能"""
        return [s for s in self._skills.values() if s.can_user_invoke()]
