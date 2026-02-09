"""
Core LLM - LLM 客户端

封装 OpenAI API 调用，提供统一的接口。
支持流式输出、工具调用等功能。
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterator, Optional, Union

from openai import OpenAI

from .exceptions import LLMConnectionError, LLMError, LLMRateLimitError, LLMResponseError
from .types import LLMResponse, Message, StreamChunk, ToolCall


class LLMClient:
    """
    LLM 客户端
    
    封装 OpenAI API，提供统一的聊天接口。
    支持流式输出、工具调用、并行工具调用。
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """
        初始化 LLM 客户端
        
        Args:
            api_key: OpenAI API Key（默认从环境变量读取）
            base_url: API Base URL（默认从环境变量读取）
            model: 模型名称（默认从环境变量读取）
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("MODEL", "gpt-4o")
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if not self.api_key:
            raise LLMConnectionError("OPENAI_API_KEY not set")
        
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    def chat(
        self,
        messages: list[Message],
        stream: bool = False,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, dict[str, Any]]] = None,
        parallel_tool_calls: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Union[LLMResponse, Iterator[StreamChunk]]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            tools: 工具定义列表
            tool_choice: 工具选择策略
            parallel_tool_calls: 是否允许并行调用工具
            temperature: 温度参数（覆盖默认值）
            max_tokens: 最大 token 数（覆盖默认值）
            **kwargs: 其他参数
            
        Returns:
            LLMResponse 或 StreamChunk 迭代器
        """
        # 转换消息格式（支持 Message 对象或 dict）
        message_dicts = [
            m.to_dict() if hasattr(m, 'to_dict') else m
            for m in messages
        ]
        
        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self.model,
            "messages": message_dicts,
            "temperature": temperature if temperature is not None else self.temperature,
            "stream": stream,
        }
        
        if self.max_tokens or max_tokens:
            request_params["max_tokens"] = max_tokens or self.max_tokens
        
        if tools:
            request_params["tools"] = tools
            if tool_choice:
                request_params["tool_choice"] = tool_choice
            request_params["parallel_tool_calls"] = parallel_tool_calls
        
        request_params.update(kwargs)
        
        try:
            if stream:
                return self._stream_chat(request_params)
            else:
                return self._sync_chat(request_params)
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str:
                raise LLMRateLimitError()
            raise LLMError(f"LLM API error: {e}")
    
    def _sync_chat(self, request_params: dict[str, Any]) -> LLMResponse:
        """同步聊天请求"""
        response = self._client.chat.completions.create(**request_params)
        
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        
        # 解析 tool_calls
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=self._parse_arguments(tc.function.arguments),
                )
                for tc in message.tool_calls
            ]
        
        # 解析 usage
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=finish_reason or "stop",
            usage=usage,
        )
    
    def _stream_chat(self, request_params: dict[str, Any]) -> Iterator[StreamChunk]:
        """流式聊天请求"""
        stream = self._client.chat.completions.create(**request_params)
        
        # 用于拼接流式 tool_calls
        tool_calls_buffer: dict[int, dict[str, Any]] = {}
        
        for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason
            
            # 处理文本内容
            content = delta.content if hasattr(delta, "content") else None
            
            # 处理 tool_calls
            tool_calls = None
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }
                    
                    if tc.id:
                        tool_calls_buffer[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_buffer[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tc.function.arguments
            
            # 如果是最后一个 chunk 且有 tool_calls
            if finish_reason:
                if tool_calls_buffer:
                    tool_calls = [
                        ToolCall(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=self._parse_arguments(tc_data["arguments"]),
                        )
                        for tc_data in tool_calls_buffer.values()
                    ]
            
            yield StreamChunk(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )
    
    def _parse_arguments(self, arguments: str) -> dict[str, Any]:
        """解析工具参数"""
        try:
            return json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return {}
    
    def chat_simple(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> str:
        """
        简单聊天（只返回文本内容）
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            响应文本
        """
        response = self.chat(messages, stream=False, **kwargs)
        if isinstance(response, LLMResponse):
            return response.content or ""
        return ""
    
    def chat_stream(
        self,
        messages: list[Message],
        on_content: Optional[callable] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        流式聊天，并在最后返回完整响应
        
        Args:
            messages: 消息列表
            on_content: 内容回调函数
            **kwargs: 其他参数
            
        Returns:
            完整的 LLMResponse
        """
        content_buffer = ""
        tool_calls = None
        finish_reason = "stop"
        
        for chunk in self.chat(messages, stream=True, **kwargs):
            if chunk.content:
                content_buffer += chunk.content
                if on_content:
                    on_content(chunk.content)
            
            if chunk.tool_calls:
                tool_calls = chunk.tool_calls
            
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
        
        return LLMResponse(
            content=content_buffer if content_buffer else None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )
