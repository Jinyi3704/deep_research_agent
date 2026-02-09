"""
Config - 配置管理

提供统一的配置管理，支持从环境变量加载。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    @classmethod
    def from_env(cls) -> LLMConfig:
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("MODEL", "gpt-4o"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )


@dataclass
class AgentConfig:
    """Agent 配置"""
    max_steps: int = 50  # 合同审核需要较多步骤
    debug: bool = False
    stream: bool = True
    tool_choice: str = "auto"
    
    @classmethod
    def from_env(cls) -> AgentConfig:
        """从环境变量加载配置"""
        return cls(
            max_steps=int(os.getenv("MAX_STEPS", "50")),
            debug=os.getenv("DEBUG", "0").lower() in {"1", "true", "yes"},
            stream=os.getenv("STREAM", "1").lower() in {"1", "true", "yes"},
        )


@dataclass
class SupabaseConfig:
    """Supabase 配置"""
    url: str = ""
    api_key: str = ""
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> SupabaseConfig:
        """从环境变量加载配置"""
        url = os.getenv("SUPABASE_URL", "")
        api_key = os.getenv("SUPABASE_API_KEY", "")
        return cls(
            url=url,
            api_key=api_key,
            enabled=bool(url and api_key),
        )


@dataclass
class LlamaCloudConfig:
    """LlamaCloud 配置"""
    api_key: str = ""
    index_id: str = ""
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> LlamaCloudConfig:
        """从环境变量加载配置"""
        api_key = os.getenv("LLAMACLOUD_API_KEY", "")
        index_id = os.getenv("LLAMACLOUD_INDEX_ID", "")
        return cls(
            api_key=api_key,
            index_id=index_id,
            enabled=bool(api_key and index_id),
        )


@dataclass
class UIConfig:
    """UI 配置"""
    show_plan: bool = False
    show_tool_log: bool = True
    show_reflection: bool = False
    
    @classmethod
    def from_env(cls) -> UIConfig:
        """从环境变量加载配置"""
        return cls(
            show_plan=os.getenv("SHOW_PLAN", "0").lower() in {"1", "true", "yes"},
            show_tool_log=os.getenv("TOOL_LOG", "1").lower() in {"1", "true", "yes"},
            show_reflection=os.getenv("REFLECT", "0").lower() in {"1", "true", "yes"},
        )


@dataclass
class AppConfig:
    """
    应用配置
    
    包含所有配置项，支持从环境变量加载。
    """
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    llamacloud: LlamaCloudConfig = field(default_factory=LlamaCloudConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    @classmethod
    def from_env(cls) -> AppConfig:
        """从环境变量加载所有配置"""
        # 尝试加载 .env 文件
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        return cls(
            llm=LLMConfig.from_env(),
            agent=AgentConfig.from_env(),
            supabase=SupabaseConfig.from_env(),
            llamacloud=LlamaCloudConfig.from_env(),
            ui=UIConfig.from_env(),
        )
    
    def validate(self) -> list[str]:
        """
        验证配置
        
        Returns:
            错误列表，如果为空则配置有效
        """
        errors = []
        
        if not self.llm.api_key:
            errors.append("OPENAI_API_KEY is not set")
        
        return errors
    
    def is_valid(self) -> bool:
        """配置是否有效"""
        return len(self.validate()) == 0


# 全局配置实例（延迟加载）
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def reload_config() -> AppConfig:
    """重新加载配置"""
    global _config
    _config = AppConfig.from_env()
    return _config
