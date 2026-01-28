from __future__ import annotations

import os
import sys
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class SupabaseClient:
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        初始化 Supabase 客户端
        
        Args:
            url: Supabase URL，如果为 None 则从环境变量 SUPABASE_URL 读取
            api_key: Supabase API Key，如果为 None 则从环境变量 SUPABASE_API_KEY 读取
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.api_key = api_key or os.getenv("SUPABASE_API_KEY")
        
        if not self.url or not self.api_key:
            raise ValueError(
                "Supabase URL and API Key must be provided either as parameters "
                "or via SUPABASE_URL and SUPABASE_API_KEY environment variables"
            )
        
        self.client: Client = create_client(self.url, self.api_key)
    
    def save_conversation(
        self,
        user_input: str,
        assistant_output: str,
        plan: Optional[str] = None,
        reflection: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        保存对话到 Supabase 数据库
        
        Args:
            user_input: 用户输入
            assistant_output: 助手回复
            plan: 规划内容（可选）
            reflection: 反思内容（可选）
            session_id: 会话 ID（可选，用于关联同一会话的多轮对话）
        
        Returns:
            保存的记录字典，如果失败则返回 None
        """
        try:
            data = {
                "user_input": user_input,
                "assistant_output": assistant_output,
            }
            
            if plan:
                data["plan"] = plan
            if reflection:
                data["reflection"] = reflection
            if session_id:
                data["session_id"] = session_id
            
            response = self.client.table("conversations").insert(data).execute()
            
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as e:
            print(f"Error saving conversation to Supabase: {e}", file=sys.stderr)
            return None
