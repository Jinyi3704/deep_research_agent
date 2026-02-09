"""
State Manager - 状态管理器

提供通用的状态管理功能，支持状态的存储、检索和重置。
使用依赖注入的方式，避免全局状态。
"""

from __future__ import annotations

from typing import Any, Optional, TypeVar, Generic

T = TypeVar("T")


class StateManager(Generic[T]):
    """
    通用状态管理器
    
    管理键值对形式的状态数据。
    支持类型安全的状态访问。
    """
    
    def __init__(self) -> None:
        self._states: dict[str, Any] = {}
    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        获取状态
        
        Args:
            key: 状态键
            default: 默认值
            
        Returns:
            状态值，如果不存在则返回默认值
        """
        return self._states.get(key, default)
    
    def set(self, key: str, value: T) -> None:
        """
        设置状态
        
        Args:
            key: 状态键
            value: 状态值
        """
        self._states[key] = value
    
    def delete(self, key: str) -> bool:
        """
        删除状态
        
        Args:
            key: 状态键
            
        Returns:
            是否删除成功
        """
        if key in self._states:
            del self._states[key]
            return True
        return False
    
    def has(self, key: str) -> bool:
        """
        检查状态是否存在
        
        Args:
            key: 状态键
            
        Returns:
            是否存在
        """
        return key in self._states
    
    def reset(self) -> None:
        """重置所有状态"""
        self._states.clear()
    
    def keys(self) -> list[str]:
        """获取所有状态键"""
        return list(self._states.keys())
    
    def items(self) -> list[tuple[str, Any]]:
        """获取所有状态键值对"""
        return list(self._states.items())
    
    def update(self, data: dict[str, Any]) -> None:
        """批量更新状态"""
        self._states.update(data)
    
    def __contains__(self, key: str) -> bool:
        return key in self._states
    
    def __len__(self) -> int:
        return len(self._states)
