"""
Core - 核心抽象层

提供 Agent 系统的核心抽象：
- types: 类型定义（Message, ToolCall, AgentResult 等）
- exceptions: 异常层次结构
- tool: 工具抽象和注册表
- llm: LLM 客户端
- base_agent: Agent 抽象基类
"""

from .types import (
    Role,
    Message,
    ToolCall,
    ToolResult,
    AgentResult,
    LLMResponse,
    StreamChunk,
    StreamCallback,
    ToolLogCallback,
)
from .exceptions import (
    AgentError,
    ToolError,
    ToolNotFoundError,
    ToolExecutionError,
    LLMError,
    MaxStepsReachedError,
    ConfigurationError,
)
from .tool import BaseTool, ToolSchema, ToolRegistry, tool
from .llm import LLMClient
from .base_agent import BaseAgent, AgentHook, LoggingHook, RunLogHook, AgentConfig

__all__ = [
    # Types
    "Role",
    "Message",
    "ToolCall",
    "ToolResult",
    "AgentResult",
    "LLMResponse",
    "StreamChunk",
    "StreamCallback",
    "ToolLogCallback",
    # Exceptions
    "AgentError",
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "LLMError",
    "MaxStepsReachedError",
    "ConfigurationError",
    # Tool
    "BaseTool",
    "ToolSchema",
    "ToolRegistry",
    "tool",
    # LLM
    "LLMClient",
    # Agent
    "BaseAgent",
    "AgentHook",
    "LoggingHook",
    "RunLogHook",
    "AgentConfig",
]
