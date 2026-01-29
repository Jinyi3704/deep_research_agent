from __future__ import annotations

from typing import Dict, List, Optional


class Planner:
    def __init__(self, llm, max_steps: int = 6) -> None:
        self.llm = llm
        self.max_steps = max_steps

    def make_plan(
        self,
        user_input: str,
        context: Optional[List[Dict[str, str]]] = None,
        skill_context: str = "",
        stream_output=None,
    ) -> str:
        system_prompt = (
            "You are a planning assistant. Create a concise, step-by-step plan "
            f"with at most {self.max_steps} steps. Use numbered steps. "
            "Return only the plan."
        )
        # 如果有 skill_context，将专家经验注入到 system prompt
        if skill_context:
            system_prompt += skill_context
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if context:
            messages.extend(context)
        messages.append(
            {
                "role": "user",
                "content": f"User request: {user_input}",
            }
        )
        if stream_output:
            stream = self.llm.chat(messages, stream=True)
            buffer = ""
            for chunk in stream:
                chunk_content = chunk.choices[0].delta.content
                if not chunk_content:
                    continue
                buffer += chunk_content
                stream_output(chunk_content)
            return buffer

        return self.llm.chat(messages, stream=False) or ""
