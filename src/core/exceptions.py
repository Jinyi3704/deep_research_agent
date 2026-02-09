"""
Core Exceptions - 异常层次结构

定义 Agent 系统中使用的所有自定义异常。
提供清晰的异常层次，便于错误处理和调试。
"""

from __future__ import annotations

from typing import Any, Optional


class AgentError(Exception):
    """
    Agent 基础异常
    
    所有 Agent 相关异常的基类。
    """
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ToolError(AgentError):
    """
    工具相关异常基类
    """
    pass


class ToolNotFoundError(ToolError):
    """
    工具未找到异常
    """
    
    def __init__(self, tool_name: str, available_tools: Optional[list[str]] = None):
        message = f"Tool not found: '{tool_name}'"
        details = {"tool_name": tool_name}
        if available_tools:
            details["available_tools"] = available_tools
        super().__init__(message, details)
        self.tool_name = tool_name
        self.available_tools = available_tools


class ToolExecutionError(ToolError):
    """
    工具执行失败异常
    """
    
    def __init__(
        self,
        tool_name: str,
        original_error: Optional[Exception] = None,
        arguments: Optional[dict[str, Any]] = None,
    ):
        message = f"Tool execution failed: '{tool_name}'"
        if original_error:
            message += f" - {original_error}"
        
        details = {"tool_name": tool_name}
        if arguments:
            details["arguments"] = arguments
        if original_error:
            details["original_error"] = str(original_error)
        
        super().__init__(message, details)
        self.tool_name = tool_name
        self.original_error = original_error
        self.arguments = arguments


class ToolValidationError(ToolError):
    """
    工具参数验证失败异常
    """
    
    def __init__(
        self,
        tool_name: str,
        validation_errors: list[str],
        arguments: Optional[dict[str, Any]] = None,
    ):
        message = f"Tool validation failed: '{tool_name}' - {', '.join(validation_errors)}"
        details = {
            "tool_name": tool_name,
            "validation_errors": validation_errors,
        }
        if arguments:
            details["arguments"] = arguments
        
        super().__init__(message, details)
        self.tool_name = tool_name
        self.validation_errors = validation_errors
        self.arguments = arguments


class LLMError(AgentError):
    """
    LLM 相关异常基类
    """
    pass


class LLMConnectionError(LLMError):
    """
    LLM 连接错误
    """
    
    def __init__(self, message: str = "Failed to connect to LLM API"):
        super().__init__(message)


class LLMResponseError(LLMError):
    """
    LLM 响应错误
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        details = {}
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body
        
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body


class LLMRateLimitError(LLMError):
    """
    LLM 速率限制错误
    """
    
    def __init__(self, retry_after: Optional[float] = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after}s"
        
        super().__init__(message, {"retry_after": retry_after})
        self.retry_after = retry_after


class MaxStepsReachedError(AgentError):
    """
    达到最大步数异常
    """
    
    def __init__(self, max_steps: int, current_step: int):
        message = f"Reached maximum steps ({max_steps})"
        super().__init__(message, {
            "max_steps": max_steps,
            "current_step": current_step,
        })
        self.max_steps = max_steps
        self.current_step = current_step


class ConfigurationError(AgentError):
    """
    配置错误异常
    """
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(message, details)
        self.config_key = config_key


class StateError(AgentError):
    """
    状态管理错误异常
    """
    
    def __init__(self, message: str, state_key: Optional[str] = None):
        details = {}
        if state_key:
            details["state_key"] = state_key
        
        super().__init__(message, details)
        self.state_key = state_key
