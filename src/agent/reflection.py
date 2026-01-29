from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class Reflector:
    def __init__(self, llm, debug: bool = False) -> None:
        self.llm = llm
        self.debug = debug

    def _parse(self, text: str, fallback: str) -> Tuple[str, str]:
        if "Final:" not in text:
            return text.strip() or fallback, ""
        before, after = text.split("Final:", 1)
        final = after.strip() or fallback
        reflection = ""
        if "Reflection:" in before:
            reflection = before.split("Reflection:", 1)[1].strip()
        return final, reflection

    def _stream_response(self, messages, stream_output) -> str:
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

    def reflect(
        self,
        user_input: str,
        answer: str,
        context: Optional[List[Dict[str, str]]] = None,
        plan: Optional[str] = None,
        skill_context: str = "",
        log_output=None,
        stream_output=None,
    ) -> Tuple[str, str]:
        system_prompt = (
            "You are a reflection assistant. Critique the draft answer for accuracy, "
            "completeness, and clarity. If you can improve it, provide a revised final answer. "
            "If no changes are needed, keep the final answer the same.\n\n"
            "Output format:\n"
            "Reflection: <short notes>\n"
            "Final: <final answer>\n"
            "Return only this format."
        )
        # 注入专家经验
        if skill_context:
            system_prompt += skill_context
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if context:
            messages.extend(context)
        if plan:
            messages.append({"role": "system", "content": "Plan:\n" + plan})
        messages.append(
            {
                "role": "user",
                "content": f"User request: {user_input}\n\nDraft answer:\n{answer}",
            }
        )
        if stream_output:
            text = self._stream_response(messages, stream_output) or ""
        else:
            text = self.llm.chat(messages, stream=False) or ""
        final, reflection = self._parse(text, answer)
        if self.debug and reflection:
            if log_output:
                log_output("[reflection] " + reflection)
            else:
                print("[reflection] " + reflection)
        return final, reflection
