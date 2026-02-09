"""
Core Base Agent - Agent 抽象基类

提供 Agent 的核心抽象和钩子系统。
所有具体的 Agent 实现都应该继承 BaseAgent。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterator, List, Optional

from .exceptions import MaxStepsReachedError
from .llm import LLMClient
from .tool import ToolRegistry
from .types import (
    AgentResult,
    LLMResponse,
    Message,
    StreamCallback,
    StreamChunk,
    ToolCall,
    ToolLogCallback,
    ToolResult,
)


@dataclass
class AgentConfig:
    """Agent 配置"""
    max_steps: int = 50  # 合同审核需要较多步骤
    debug: bool = False
    stream: bool = True
    tool_choice: str = "auto"


class AgentHook(ABC):
    """
    Agent 钩子抽象基类
    
    用于在 Agent 执行过程中插入自定义逻辑（日志、监控等）。
    """
    
    def on_agent_start(self, input: str, context: Optional[list[Message]] = None) -> None:
        """Agent 开始执行"""
        pass
    
    def on_agent_end(self, result: AgentResult) -> None:
        """Agent 执行结束"""
        pass
    
    def on_llm_start(self, messages: list[Message]) -> None:
        """LLM 调用开始"""
        pass
    
    def on_llm_end(self, response: LLMResponse) -> None:
        """LLM 调用结束"""
        pass
    
    def on_tool_start(self, tool_call: ToolCall) -> None:
        """工具调用开始"""
        pass
    
    def on_tool_end(self, tool_call: ToolCall, result: ToolResult) -> None:
        """工具调用结束"""
        pass
    
    def on_step(self, step: int, message: Optional[str] = None) -> None:
        """执行步骤"""
        pass
    
    def on_error(self, error: Exception) -> None:
        """发生错误"""
        pass


class LoggingHook(AgentHook):
    """
    日志钩子
    
    输出 Agent 执行过程的日志。
    """
    
    def __init__(
        self,
        log_func: Optional[Callable[[str], None]] = None,
        verbose: bool = False,
    ):
        self.log_func = log_func or print
        self.verbose = verbose
    
    def _log(self, message: str) -> None:
        self.log_func(message)
    
    def on_agent_start(self, input: str, context: Optional[list[Message]] = None) -> None:
        if self.verbose:
            self._log(f"[agent] Starting with input: {input[:100]}...")
    
    def on_agent_end(self, result: AgentResult) -> None:
        if self.verbose:
            self._log(f"[agent] Finished with reason: {result.finish_reason}")
    
    def on_tool_start(self, tool_call: ToolCall) -> None:
        args_str = str(tool_call.arguments)
        self._log(f"[tool] Calling {tool_call.name}({args_str})")
    
    def on_tool_end(self, tool_call: ToolCall, result: ToolResult) -> None:
        status = "✓" if result.success else "✗"
        self._log(f"[tool] {tool_call.name} {status} -> {result.content}")
    
    def on_step(self, step: int, message: Optional[str] = None) -> None:
        if self.verbose:
            self._log(f"[step {step}] {message or ''}")
    
    def on_error(self, error: Exception) -> None:
        self._log(f"[error] {error}")


class RunLogHook(AgentHook):
    """
    运行日志钩子
    
    将每次大模型输出和工具输出追加到指定列表，
    便于保存为「大模型与工具」日志（与会话日志一起保存）。
    """

    def __init__(self, log_list: List[dict]) -> None:
        self._log_list = log_list

    def _append(self, role: str, content: str) -> None:
        self._log_list.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "role": role,
            "content": content,
        })

    def on_llm_end(self, response: LLMResponse) -> None:
        parts = []
        if response.content:
            parts.append(response.content)
        if response.tool_calls:
            names = [tc.name for tc in response.tool_calls]
            parts.append(f"\n[工具调用] {', '.join(names)}")
        self._append("大模型", "\n".join(parts) if parts else "(无文本)")

    def on_tool_end(self, tool_call: ToolCall, result: ToolResult) -> None:
        header = f"{tool_call.name}"
        if not result.success and result.error:
            header += f" (失败: {result.error})"
        self._append("工具", f"{header}\n\n{result.content}")


class BaseAgent(ABC):
    """
    Agent 抽象基类
    
    提供 Agent 的核心功能：
    - LLM 调用
    - 工具执行
    - 钩子系统
    - 消息管理
    """
    
    def __init__(
        self,
        llm: LLMClient,
        tools: Optional[ToolRegistry] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        初始化 Agent
        
        Args:
            llm: LLM 客户端
            tools: 工具注册表（可选）
            config: Agent 配置（可选）
        """
        self.llm = llm
        self.tools = tools or ToolRegistry()
        self.config = config or AgentConfig()
        self._hooks: list[AgentHook] = []
    
    def add_hook(self, hook: AgentHook) -> None:
        """添加钩子"""
        self._hooks.append(hook)
    
    def remove_hook(self, hook: AgentHook) -> None:
        """移除钩子"""
        if hook in self._hooks:
            self._hooks.remove(hook)
    
    @abstractmethod
    def run(
        self,
        input: str,
        context: Optional[list[Message]] = None,
        stream_output: Optional[StreamCallback] = None,
        tool_log_output: Optional[ToolLogCallback] = None,
        **kwargs: Any,
    ) -> AgentResult:
        """
        执行 Agent 主逻辑
        
        Args:
            input: 用户输入
            context: 上下文消息列表
            stream_output: 流式输出回调
            tool_log_output: 工具日志回调
            **kwargs: 其他参数
            
        Returns:
            AgentResult
        """
        pass
    
    def _notify_agent_start(self, input: str, context: Optional[list[Message]] = None) -> None:
        """通知钩子：Agent 开始"""
        for hook in self._hooks:
            hook.on_agent_start(input, context)
    
    def _notify_agent_end(self, result: AgentResult) -> None:
        """通知钩子：Agent 结束"""
        for hook in self._hooks:
            hook.on_agent_end(result)
    
    def _notify_llm_start(self, messages: list[Message]) -> None:
        """通知钩子：LLM 调用开始"""
        for hook in self._hooks:
            hook.on_llm_start(messages)
    
    def _notify_llm_end(self, response: LLMResponse) -> None:
        """通知钩子：LLM 调用结束"""
        for hook in self._hooks:
            hook.on_llm_end(response)
    
    def _notify_tool_start(self, tool_call: ToolCall) -> None:
        """通知钩子：工具调用开始"""
        for hook in self._hooks:
            hook.on_tool_start(tool_call)
    
    def _notify_tool_end(self, tool_call: ToolCall, result: ToolResult) -> None:
        """通知钩子：工具调用结束"""
        for hook in self._hooks:
            hook.on_tool_end(tool_call, result)
    
    def _notify_step(self, step: int, message: Optional[str] = None) -> None:
        """通知钩子：执行步骤"""
        for hook in self._hooks:
            hook.on_step(step, message)
    
    def _notify_error(self, error: Exception) -> None:
        """通知钩子：发生错误"""
        for hook in self._hooks:
            hook.on_error(error)
    
    def _call_llm(
        self,
        messages: list[Message],
        stream: bool = False,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> LLMResponse | Iterator[StreamChunk]:
        """
        调用 LLM
        
        这是 Agent 内部调用 LLM 的统一入口，会触发相应的钩子。
        """
        self._notify_llm_start(messages)
        
        try:
            response = self.llm.chat(
                messages=messages,
                stream=stream,
                tools=tools,
                **kwargs,
            )
            
            if not stream and isinstance(response, LLMResponse):
                self._notify_llm_end(response)
            
            return response
        except Exception as e:
            self._notify_error(e)
            raise
    
    def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall],
        tool_log_output: Optional[ToolLogCallback] = None,
    ) -> list[ToolResult]:
        """
        执行工具调用
        
        这是 Agent 内部执行工具的统一入口，会触发相应的钩子。
        """
        results: list[ToolResult] = []
        
        for tool_call in tool_calls:
            self._notify_tool_start(tool_call)
            
            try:
                result = self.tools.execute_tool_call(tool_call)
            except Exception as e:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=f"Error: {e}",
                    success=False,
                    error=str(e),
                )
                self._notify_error(e)
            
            self._notify_tool_end(tool_call, result)
            
            # 输出工具日志
            if tool_log_output:
                status = "✓" if result.success else "✗"
                tool_log_output(f"[tool] {tool_call.name} {status} -> {result.content}")
            
            results.append(result)
        
        return results
    
    def _build_system_prompt(self, **kwargs: Any) -> str:
        """
        构建系统提示词
        
        子类可以重写此方法来自定义系统提示词。
        """
        return (
            "You are a helpful assistant with access to tools. "
            "Use tools when they can help answer the user's question accurately. "
            "When you have gathered enough information, provide a clear and complete answer. "
            "Respond in the user's language."
        )
    
    def _process_stream_response(
        self,
        stream: Iterator[StreamChunk],
        stream_output: Optional[StreamCallback] = None,
    ) -> tuple[str, list[ToolCall], str]:
        """
        处理流式响应
        
        Args:
            stream: StreamChunk 迭代器
            stream_output: 流式输出回调
            
        Returns:
            (content, tool_calls, finish_reason)
        """
        content_buffer = ""
        tool_calls: list[ToolCall] = []
        finish_reason = "stop"
        
        for chunk in stream:
            if chunk.content:
                content_buffer += chunk.content
                if stream_output:
                    stream_output(chunk.content)
            
            if chunk.tool_calls:
                tool_calls = chunk.tool_calls
            
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
        
        return content_buffer, tool_calls, finish_reason
