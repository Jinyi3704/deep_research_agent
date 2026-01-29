from __future__ import annotations

import uuid
from typing import Optional, Union

from agent.planner import Planner
from agent.react_agent import ReActAgent
from agent.reflection import Reflector
from memory import MemoryManager
from skills import Skill, SkillMatcher, LLMSkillMatcher
from tools import ToolRegistry


class AgentOrchestrator:
    def __init__(
        self,
        llm,
        tools: ToolRegistry,
        memory: Optional[MemoryManager] = None,
        planner: Optional[Planner] = None,
        react_agent: Optional[ReActAgent] = None,
        reflector: Optional[Reflector] = None,
        skill_matcher: Optional[Union[SkillMatcher, LLMSkillMatcher]] = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.memory = memory or MemoryManager(llm)
        self.planner = planner or Planner(llm)
        self.react_agent = react_agent or ReActAgent(llm, tools)
        self.reflector = reflector
        self.skill_matcher = skill_matcher
        self.last_plan: str = ""
        self.last_reflection: str = ""
        self.current_skill: Optional[Skill] = None
        self.session_id: str = str(uuid.uuid4())

    def run(
        self,
        user_input: str,
        stream_output=None,
        plan_stream_output=None,
        plan_done=None,
        tool_log_output=None,
        reflection_log_output=None,
        reflection_stream_output=None,
        skill_log_output=None,
    ) -> str:
        # 1. 匹配技能
        skill = None
        skill_arguments = ""
        skill_context = ""
        actual_user_input = user_input
        
        if self.skill_matcher:
            # 首先检查用户是否显式调用 /command
            command_match = self.skill_matcher.match_user_command(user_input)
            if command_match:
                skill, skill_arguments = command_match
                if skill_log_output:
                    skill_log_output(f"[skill] 用户调用技能: /{skill.name} {skill_arguments}")
                # 将原始输入替换为 arguments（如果有的话）
                actual_user_input = skill_arguments if skill_arguments else f"执行 {skill.name} 技能"
            else:
                # 否则让 Claude 自动匹配
                skill = self.skill_matcher.match_for_model(user_input)
                if skill and skill_log_output:
                    skill_log_output(f"[skill] 自动匹配技能: {skill.name}")
            
            self.current_skill = skill
            if skill:
                skill_context = skill.get_system_prompt_addition(
                    arguments=skill_arguments,
                    session_id=self.session_id,
                )

        # 2. 获取上下文
        context = self.memory.get_context()

        # 3. 规划（注入 skill_context）
        plan = self.planner.make_plan(
            actual_user_input,
            context,
            skill_context=skill_context,
            stream_output=plan_stream_output,
        )
        self.last_plan = plan
        if plan_done:
            plan_done(plan)

        # 4. 执行（注入 skill_context）
        answer = self.react_agent.run(
            actual_user_input,
            context=context,
            plan=plan,
            skill_context=skill_context,
            stream_output=stream_output,
            tool_log_output=tool_log_output,
        )

        # 5. 反思
        reflection = None
        if self.reflector:
            answer, reflection = self.reflector.reflect(
                actual_user_input,
                answer,
                context=context,
                plan=plan,
                skill_context=skill_context,
                log_output=reflection_log_output,
                stream_output=reflection_stream_output,
            )
            self.last_reflection = reflection

        # 6. 保存到记忆（使用原始用户输入）
        self.memory.add_interaction(
            user_input,
            answer,
            plan=plan,
            reflection=reflection,
        )
        return answer

    def get_available_commands(self) -> list[str]:
        """获取所有可用的 /command 列表"""
        if self.skill_matcher:
            return self.skill_matcher.get_available_commands()
        return []

    def get_skill_descriptions(self) -> str:
        """获取所有可用技能的描述"""
        if self.skill_matcher:
            return self.skill_matcher.get_skill_descriptions()
        return ""
