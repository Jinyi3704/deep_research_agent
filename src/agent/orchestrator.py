from __future__ import annotations

from typing import Optional

from agent.planner import Planner
from agent.react_agent import ReActAgent
from agent.reflection import Reflector
from memory import MemoryManager
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
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.memory = memory or MemoryManager(llm)
        self.planner = planner or Planner(llm)
        self.react_agent = react_agent or ReActAgent(llm, tools)
        self.reflector = reflector
        self.last_plan: str = ""
        self.last_reflection: str = ""

    def run(
        self,
        user_input: str,
        stream_output=None,
        plan_stream_output=None,
        plan_done=None,
        tool_log_output=None,
        reflection_log_output=None,
        reflection_stream_output=None,
    ) -> str:
        context = self.memory.get_context()
        plan = self.planner.make_plan(user_input, context, stream_output=plan_stream_output)
        self.last_plan = plan
        if plan_done:
            plan_done(plan)
        answer = self.react_agent.run(
            user_input,
            context=context,
            plan=plan,
            stream_output=stream_output,
            tool_log_output=tool_log_output,
        )
        if self.reflector:
            answer, reflection = self.reflector.reflect(
                user_input,
                answer,
                context=context,
                plan=plan,
                log_output=reflection_log_output,
                stream_output=reflection_stream_output,
            )
            self.last_reflection = reflection
        self.memory.add_interaction(user_input, answer)
        return answer
