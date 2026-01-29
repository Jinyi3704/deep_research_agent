from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from tools import ToolRegistry


class ReActAgent:
    def __init__(self, llm, tools: ToolRegistry, max_steps: int = 6, debug: bool = False) -> None:
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.debug = debug
        self.history: List[Dict[str, str]] = []

    def _system_prompt(self, plan: Optional[str] = None, skill_context: str = "") -> str:
        tool_lines = []
        for tool in self.tools.list():
            params = json.dumps(tool.parameters, ensure_ascii=True)
            tool_lines.append(f"- {tool.name}: {tool.description} Parameters: {params}")
        tools_block = "\n".join(tool_lines) if tool_lines else "- (no tools registered)"

        parts = [
            "You are a tool-using assistant. Use tools when they are helpful.",
            f"Available tools:\n{tools_block}",
        ]
        # 注入专家经验
        if skill_context:
            parts.append(skill_context)
        if plan:
            parts.append("Plan:\n" + plan + "\nFollow the plan but adjust if needed.")
        parts.extend(
            [
                "When you need a tool, respond with exactly:\n"
                "Action: <tool_name>\n"
                "Action Input: <json>",
                "When you have the final answer, respond with exactly:\n"
                "Final: <answer>",
                "Do not include any other text. Respond in the user's language.",
            ]
        )
        return "\n\n".join(parts)

    def _parse_action(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        action_match = re.search(r"Action:\s*(.+)", text)
        if not action_match:
            return None
        name = action_match.group(1).strip().split()[0]

        input_match = re.search(r"Action Input:\s*(.+)", text, re.S)
        raw_input = input_match.group(1).strip() if input_match else ""
        if raw_input.startswith("```"):
            raw_input = re.sub(r"^```[a-zA-Z]*\n", "", raw_input)
            raw_input = re.sub(r"\n```$", "", raw_input).strip()

        parsed_input: Dict[str, Any]
        if raw_input:
            try:
                parsed_input = json.loads(raw_input)
            except json.JSONDecodeError:
                parsed_input = {"input": raw_input}
        else:
            parsed_input = {}
        return name, parsed_input

    def _parse_final(self, text: str) -> Optional[str]:
        if "Final:" not in text:
            return None
        return text.split("Final:", 1)[1].strip()

    def _call_tool(self, name: str, action_input: Dict[str, Any]) -> str:
        tool = self.tools.get(name)
        if not tool:
            available = ", ".join(self.tools.names()) or "none"
            return f"Unknown tool '{name}'. Available tools: {available}"
        try:
            return tool.func(action_input)
        except Exception as exc:
            return f"Tool error: {exc}"

    def _log_tool(self, message: str, tool_log_output=None) -> None:
        if not self.debug:
            return
        if tool_log_output:
            tool_log_output(message)
        else:
            print(message)

    def _stream_response(
        self,
        messages: List[Dict[str, str]],
        stream_output,
    ) -> str:
        stream = self.llm.chat(messages, stream=True)
        buffer = ""
        final_start: Optional[int] = None
        printed = 0
        for chunk in stream:
            chunk_content = chunk.choices[0].delta.content
            if not chunk_content:
                continue
            buffer += chunk_content
            if final_start is None:
                idx = buffer.find("Final:")
                if idx != -1:
                    final_start = idx + len("Final:")
                    to_print = buffer[final_start:]
                    if to_print:
                        stream_output(to_print)
                        printed = len(to_print)
            else:
                to_print = buffer[final_start + printed :]
                if to_print:
                    stream_output(to_print)
                    printed += len(to_print)
        return buffer

    def run(
        self,
        user_input: str,
        context: Optional[List[Dict[str, str]]] = None,
        plan: Optional[str] = None,
        skill_context: str = "",
        stream_output=None,
        tool_log_output=None,
    ) -> str:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._system_prompt(plan, skill_context)}
        ]
        if context:
            messages.extend(context)
        elif self.history:
            messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_steps):
            if stream_output:
                assistant_text = self._stream_response(messages, stream_output) or ""
            else:
                assistant_text = self.llm.chat(messages, stream=False) or ""
            final_text = self._parse_final(assistant_text)
            if final_text is not None:
                if context is None:
                    self.history.append({"role": "user", "content": user_input})
                    self.history.append({"role": "assistant", "content": final_text})
                return final_text

            action = self._parse_action(assistant_text)
            if action is None:
                if context is None:
                    self.history.append({"role": "user", "content": user_input})
                    self.history.append({"role": "assistant", "content": assistant_text})
                return assistant_text

            name, action_input = action
            observation = self._call_tool(name, action_input)
            self._log_tool(f"[tool] {name}({action_input}) -> {observation}", tool_log_output)

            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": f"Observation: {observation}"})

        return "Reached the maximum number of tool steps without a final answer."
