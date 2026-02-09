"""
Core Tool - 工具抽象和注册表

提供工具系统的核心抽象：
- BaseTool: 工具抽象基类
- ToolSchema: 工具 Schema 定义
- ToolRegistry: 工具注册表
- @tool: 工具装饰器
"""

from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, get_type_hints

from .exceptions import ToolExecutionError, ToolNotFoundError, ToolValidationError
from .types import ToolCall, ToolResult


@dataclass
class ToolSchema:
    """
    工具 Schema 定义
    
    遵循 OpenAI Function Calling 的 JSON Schema 格式。
    """
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": [],
    })
    strict: bool = False
    
    def to_openai_format(self) -> dict[str, Any]:
        """转换为 OpenAI API 格式"""
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
        if self.strict:
            schema["function"]["strict"] = True
        return schema


class BaseTool(ABC):
    """
    工具抽象基类
    
    所有工具必须继承此类并实现 schema 和 execute 方法。
    """
    
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """返回工具的 Schema 定义"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            工具执行结果（字符串）
        """
        pass
    
    @property
    def name(self) -> str:
        """工具名称"""
        return self.schema.name
    
    @property
    def description(self) -> str:
        """工具描述"""
        return self.schema.description
    
    def to_openai_format(self) -> dict[str, Any]:
        """转换为 OpenAI API 格式"""
        return self.schema.to_openai_format()
    
    def __call__(self, **kwargs: Any) -> str:
        """允许直接调用工具"""
        return self.execute(**kwargs)


class FunctionTool(BaseTool):
    """
    基于函数的工具实现
    
    将普通函数包装为 BaseTool。
    """
    
    def __init__(
        self,
        func: Callable[..., str],
        name: str,
        description: str,
        parameters: dict[str, Any],
        strict: bool = False,
    ):
        self._func = func
        self._schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            strict=strict,
        )
    
    @property
    def schema(self) -> ToolSchema:
        return self._schema
    
    def execute(self, **kwargs: Any) -> str:
        return self._func(**kwargs)


def _python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """将 Python 类型转换为 JSON Schema 类型"""
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    
    # 处理 Optional 类型
    origin = getattr(py_type, "__origin__", None)
    if origin is type(None):
        return {"type": "null"}
    
    # 获取基础类型
    if py_type in type_mapping:
        return type_mapping[py_type]
    
    # 默认为字符串
    return {"type": "string"}


def _generate_parameters_schema(func: Callable) -> dict[str, Any]:
    """从函数签名自动生成参数 Schema"""
    sig = inspect.signature(func)
    hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}
    
    properties: dict[str, Any] = {}
    required: list[str] = []
    
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        
        # 获取类型
        param_type = hints.get(param_name, str)
        schema = _python_type_to_json_schema(param_type)
        
        # 添加描述（从 docstring 提取，暂时留空）
        properties[param_name] = schema
        
        # 检查是否必需
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[dict[str, Any]] = None,
    strict: bool = False,
) -> Callable[[Callable[..., str]], FunctionTool]:
    """
    工具装饰器
    
    将函数转换为 BaseTool 实例。
    
    Usage:
        @tool(name="calculator", description="计算数学表达式")
        def calculate(expression: str) -> str:
            return str(eval(expression))
    """
    def decorator(func: Callable[..., str]) -> FunctionTool:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"
        tool_parameters = parameters or _generate_parameters_schema(func)
        
        return FunctionTool(
            func=func,
            name=tool_name,
            description=tool_description,
            parameters=tool_parameters,
            strict=strict,
        )
    
    return decorator


class ToolRegistry:
    """
    工具注册表
    
    管理所有注册的工具，提供工具的注册、查找和调用功能。
    """
    
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: BaseTool 实例
        """
        self._tools[tool.name] = tool
    
    def register_function(
        self,
        func: Callable[..., str],
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
        strict: bool = False,
    ) -> FunctionTool:
        """
        注册函数为工具
        
        Args:
            func: 工具函数
            name: 工具名称（默认使用函数名）
            description: 工具描述
            parameters: 参数 Schema
            strict: 是否启用严格模式
            
        Returns:
            创建的 FunctionTool 实例
        """
        tool_instance = FunctionTool(
            func=func,
            name=name or func.__name__,
            description=description or func.__doc__ or f"Tool: {name or func.__name__}",
            parameters=parameters or _generate_parameters_schema(func),
            strict=strict,
        )
        self.register(tool_instance)
        return tool_instance
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            BaseTool 实例，如果不存在则返回 None
        """
        return self._tools.get(name)
    
    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        调用工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            ToolResult 包含执行结果
            
        Raises:
            ToolNotFoundError: 工具不存在
        """
        tool = self.get(name)
        if not tool:
            raise ToolNotFoundError(name, list(self._tools.keys()))
        
        try:
            result = tool.execute(**arguments)
            return ToolResult(
                tool_call_id="",  # 由调用方设置
                name=name,
                content=result,
                success=True,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id="",
                name=name,
                content=f"Error: {e}",
                success=False,
                error=str(e),
            )
    
    def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        执行 ToolCall
        
        Args:
            tool_call: ToolCall 对象
            
        Returns:
            ToolResult
        """
        result = self.call(tool_call.name, tool_call.arguments)
        result.tool_call_id = tool_call.id
        return result
    
    def list(self) -> list[BaseTool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def names(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def to_openai_format(self) -> list[dict[str, Any]]:
        """
        转换为 OpenAI API 格式
        
        Returns:
            工具定义列表，可直接传递给 OpenAI API
        """
        return [tool.to_openai_format() for tool in self._tools.values()]
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
    
    def __iter__(self):
        return iter(self._tools.values())
