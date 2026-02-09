from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from memory.supabase_client import SupabaseClient


class MemoryManager:
    def __init__(
        self,
        llm=None,
        max_messages: int = 20,
        summary_trigger: int = 30,
        summary_keep: int = 6,
        supabase_client: Optional[SupabaseClient] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.max_messages = max_messages
        self.summary_trigger = summary_trigger
        self.summary_keep = summary_keep
        self.messages: List[Dict[str, str]] = []
        self.summary: str = ""
        self.supabase_client = supabase_client
        self.session_id = session_id or str(uuid.uuid4())

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def add_interaction(
        self,
        user_input: str,
        assistant_output: str,
        plan: Optional[str] = None,
        reflection: Optional[str] = None,
    ) -> None:
        self.add_message("user", user_input)
        self.add_message("assistant", assistant_output)
        
        # 保存到 Supabase
        if self.supabase_client:
            self.supabase_client.save_conversation(
                user_input=user_input,
                assistant_output=assistant_output,
                plan=plan,
                reflection=reflection,
                session_id=self.session_id,
            )
        
        self._maybe_summarize()

    def get_context(self) -> List[Dict[str, str]]:
        context: List[Dict[str, str]] = []
        if self.summary:
            context.append(
                {
                    "role": "system",
                    "content": "Summary of previous conversation:\n" + self.summary,
                }
            )
        context.extend(self.messages[-self.max_messages :])
        return context

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _maybe_summarize(self) -> None:
        if len(self.messages) <= self.summary_trigger:
            return

        if not self.llm:
            self.messages = self.messages[-self.max_messages :]
            return

        older_messages = self.messages[: -self.summary_keep]
        if not older_messages:
            return

        prompt = (
            "Summarize the conversation for future context. Keep key facts, "
            "user preferences, decisions, and tasks. Be concise."
        )
        summary_input = self._format_messages(older_messages)
        if self.summary:
            summary_input = (
                f"Existing summary:\n{self.summary}\n\nNew conversation:\n{summary_input}"
            )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": summary_input},
        ]
        response = self.llm.chat(messages, stream=False)
        summary_text = response.content if response and hasattr(response, 'content') and response.content else ""
        self.summary = summary_text.strip()
        self.messages = self.messages[-self.summary_keep :]
