"""
AI 合同审核智能体

专业的合同审核智能体框架，支持：
- 合同文档解析和章节拆分
- 逐章节审核和问题识别
- 法律知识库查询 (RAG)
- 深度推理分析
- 审核报告导出
"""

__version__ = "2.0.0"

# Core exports
from core import (
    # Types
    Role,
    Message,
    ToolCall,
    ToolResult,
    AgentResult,
    LLMResponse,
    # Exceptions
    AgentError,
    ToolError,
    LLMError,
    # Tool
    BaseTool,
    ToolSchema,
    ToolRegistry,
    tool,
    # LLM
    LLMClient,
    # Agent
    BaseAgent,
    AgentHook,
    LoggingHook,
)

# Agent exports
from agents import ContractReviewAgent

# State exports
from state import (
    StateManager,
    ReviewState,
)

# Config exports
from config import (
    AppConfig,
    LLMConfig,
    AgentConfig,
    get_config,
)

__all__ = [
    # Version
    "__version__",
    # Types
    "Role",
    "Message",
    "ToolCall",
    "ToolResult",
    "AgentResult",
    "LLMResponse",
    # Exceptions
    "AgentError",
    "ToolError",
    "LLMError",
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
    "ContractReviewAgent",
    # State
    "StateManager",
    "ReviewState",
    # Config
    "AppConfig",
    "LLMConfig",
    "AgentConfig",
    "get_config",
]
