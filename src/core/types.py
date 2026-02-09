"""
Core Types - 核心类型定义

定义 Agent 系统中使用的所有核心数据类型。
使用 dataclasses 实现，保持轻量和 Python 原生。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterator, Literal, Optional, Union


class Role(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """
    工具调用信息
    
    对应 OpenAI API 中的 tool_calls 结构
    """
    id: str
    name: str
    arguments: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """转换为 OpenAI API 格式"""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments if isinstance(self.arguments, str) else __import__("json").dumps(self.arguments),
            },
        }


@dataclass
class Message:
    """
    消息对象
    
    统一的消息格式，兼容 OpenAI API。
    """
    role: Role
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为 OpenAI API 格式的字典"""
        result: dict[str, Any] = {"role": self.role.value}
        
        if self.content is not None:
            result["content"] = self.content
        
        if self.name is not None:
            result["name"] = self.name
        
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        
        return result
    
    @classmethod
    def system(cls, content: str) -> Message:
        """创建系统消息"""
        return cls(role=Role.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> Message:
        """创建用户消息"""
        return cls(role=Role.USER, content=content)
    
    @classmethod
    def assistant(
        cls,
        content: Optional[str] = None,
        tool_calls: Optional[list[ToolCall]] = None,
    ) -> Message:
        """创建助手消息"""
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)
    
    @classmethod
    def tool(cls, tool_call_id: str, content: str) -> Message:
        """创建工具结果消息"""
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """从字典创建消息"""
        role = Role(data["role"])
        tool_calls = None
        if "tool_calls" in data and data["tool_calls"]:
            tool_calls = [
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=tc.get("function", {}).get("arguments", {}),
                )
                for tc in data["tool_calls"]
            ]
        
        return cls(
            role=role,
            content=data.get("content"),
            name=data.get("name"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
        )


@dataclass
class ToolResult:
    """
    工具执行结果
    """
    tool_call_id: str
    name: str
    content: str
    success: bool = True
    error: Optional[str] = None
    
    def to_message(self) -> Message:
        """转换为工具消息"""
        return Message.tool(self.tool_call_id, self.content)


@dataclass
class StreamChunk:
    """
    流式响应块
    """
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    finish_reason: Optional[str] = None
    
    @property
    def is_done(self) -> bool:
        """是否是最后一个块"""
        return self.finish_reason is not None


@dataclass
class LLMResponse:
    """
    LLM 响应
    """
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    finish_reason: Literal["stop", "tool_calls", "length", "content_filter"] = "stop"
    usage: Optional[dict[str, int]] = None
    
    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return bool(self.tool_calls)
    
    def to_message(self) -> Message:
        """转换为助手消息"""
        return Message.assistant(content=self.content, tool_calls=self.tool_calls)


FinishReason = Literal["stop", "tool_calls", "length", "error", "max_steps"]


@dataclass
class AgentResult:
    """
    Agent 执行结果
    
    包含完整的执行信息，便于调试和追踪。
    """
    content: str
    finish_reason: FinishReason = "stop"
    messages: list[Message] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        """执行是否成功"""
        return self.finish_reason in ("stop", "tool_calls")
    
    @property
    def tool_call_count(self) -> int:
        """工具调用次数"""
        return len(self.tool_results)


# Type aliases
StreamCallback = Callable[[str], None]
ToolLogCallback = Callable[[str], None]
MessageList = list[Message]
