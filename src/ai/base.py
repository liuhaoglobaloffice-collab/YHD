"""
AI Provider Base Classes

定义所有 AI Provider 的抽象基类和通用配置。
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, AsyncIterator


class ModelCapability(str, Enum):
    """AI 模型能力枚举"""
    TEXT_GENERATION = "text_generation"
    EMBEDDINGS = "embeddings"
    STREAMING = "streaming"
    CHAT = "chat"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    AUDIO = "audio"


@dataclass
class ProviderConfig:
    """AI Provider 配置基类"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    extra_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class AIProvider(ABC):
    """
    AI Provider 抽象基类
    
    所有 AI Provider (OpenAI, Claude, Ollama 等) 必须继承此类。
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[ModelCapability]:
        """Provider 支持的能力列表"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        生成文本（非流式）
        
        Args:
            prompt: 用户输入
            system: 系统提示词
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成文本
        
        Args:
            prompt: 用户输入
            system: 系统提示词
            **kwargs: 额外参数
            
        Yields:
            生成的文本片段
        """
        pass

    async def embed(self, text: str, **kwargs) -> List[float]:
        """
        生成文本嵌入向量
        
        Args:
            text: 输入文本
            **kwargs: 额外参数
            
        Returns:
            嵌入向量
            
        Raises:
            NotImplementedError: 如果 Provider 不支持 embeddings
        """
        raise NotImplementedError(
            f"{self.name} does not support embeddings"
        )

    def supports(self, capability: ModelCapability) -> bool:
        """检查是否支持某个能力"""
        return capability in self.capabilities

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.config.model})"
