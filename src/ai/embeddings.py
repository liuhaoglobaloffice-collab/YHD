"""
Week 4 Day 3: 文本嵌入 Providers

支持多种嵌入模型:
1. OllamaEmbedding - 使用 Ollama 本地模型
2. SentenceTransformerEmbedding - HuggingFace sentence-transformers
3. ChromaDefaultEmbedding - ChromaDB 默认嵌入
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingProvider(ABC):
    """嵌入 Provider 抽象基类"""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        将文本转换为向量

        Args:
            text: 输入文本

        Returns:
            向量 (维度取决于模型)
        """
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量嵌入文本

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        获取向量维度

        Returns:
            向量维度
        """
        pass


class OllamaEmbedding(EmbeddingProvider):
    """
    Ollama 嵌入 Provider
    
    使用 Ollama 的 embedding 模型 (如 mxbai-embed-large)
    """

    def __init__(
        self,
        model: str = "mxbai-embed-large",
        host: str = "http://localhost:11434",
    ):
        """
        初始化 Ollama Embedding

        Args:
            model: Ollama 嵌入模型名称
            host: Ollama 服务地址
        """
        self.model = model
        self.host = host
        self._client = None
        self._dimension = None  # 延迟获取

        logger.info(
            "ollama_embedding_initialized",
            model=model,
            host=host,
        )

    def _get_client(self):
        """惰性加载 Ollama 客户端"""
        if self._client is None:
            try:
                import ollama

                self._client = ollama.AsyncClient(host=self.host)
            except ImportError:
                raise ImportError(
                    "Ollama SDK not installed. Install with: pip install ollama"
                )
        return self._client

    async def embed_text(self, text: str) -> List[float]:
        """使用 Ollama 嵌入单个文本"""
        client = self._get_client()

        try:
            response = await client.embeddings(model=self.model, prompt=text)
            embedding = response["embedding"]

            # 缓存维度
            if self._dimension is None:
                self._dimension = len(embedding)

            logger.debug(
                "ollama_text_embedded",
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error(
                "ollama_embedding_failed",
                model=self.model,
                error=str(e),
            )
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)

        logger.info(
            "ollama_texts_embedded",
            count=len(texts),
        )

        return embeddings

    def get_dimension(self) -> int:
        """
        获取向量维度
        
        注意: 需要先调用一次 embed_text 才能确定维度
        """
        if self._dimension is None:
            # 默认维度 (mxbai-embed-large)
            return 1024
        return self._dimension


class SentenceTransformerEmbedding(EmbeddingProvider):
    """
    Sentence-Transformers 嵌入 Provider
    
    使用 HuggingFace sentence-transformers 库
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化 Sentence-Transformer

        Args:
            model_name: 模型名称
        """
        self.model_name = model_name
        self._model = None

        logger.info(
            "sentence_transformer_embedding_initialized",
            model=model_name,
        )

    def _get_model(self):
        """惰性加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info(
                    "sentence_transformer_model_loaded",
                    model=self.model_name,
                )
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    async def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        model = self._get_model()
        
        # sentence-transformers 是同步的，但我们用 async 接口保持一致
        embedding = model.encode(text, convert_to_numpy=True)
        
        logger.debug(
            "sentence_transformer_text_embedded",
            text_length=len(text),
            embedding_dim=len(embedding),
        )

        return embedding.tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        model = self._get_model()
        
        # 批量编码更高效
        embeddings = model.encode(texts, convert_to_numpy=True)
        
        logger.info(
            "sentence_transformer_texts_embedded",
            count=len(texts),
        )

        return [emb.tolist() for emb in embeddings]

    def get_dimension(self) -> int:
        """获取向量维度"""
        model = self._get_model()
        return model.get_sentence_embedding_dimension()


class ChromaDefaultEmbedding(EmbeddingProvider):
    """
    ChromaDB 默认嵌入 Provider
    
    使用 ChromaDB 内置的默认嵌入函数
    """

    def __init__(self):
        """初始化 Chroma 默认嵌入"""
        try:
            from chromadb.utils import embedding_functions
            
            self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            logger.info("chroma_default_embedding_initialized")
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )

    async def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        # Chroma的嵌入函数接受列表
        embeddings = self._embedding_fn([text])
        return embeddings[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        return self._embedding_fn(texts)

    def get_dimension(self) -> int:
        """获取向量维度 (ChromaDB 默认384维)"""
        return 384


def create_embedding_provider(
    provider_type: str = "chroma_default",
    **kwargs,
) -> EmbeddingProvider:
    """
    工厂函数：创建嵌入 Provider

    Args:
        provider_type: Provider 类型
            - "ollama": Ollama 嵌入
            - "sentence_transformer": Sentence-Transformers
            - "chroma_default": ChromaDB 默认嵌入
        **kwargs: Provider 特定参数

    Returns:
        EmbeddingProvider 实例
    """
    if provider_type == "ollama":
        return OllamaEmbedding(**kwargs)
    elif provider_type == "sentence_transformer":
        return SentenceTransformerEmbedding(**kwargs)
    elif provider_type == "chroma_default":
        return ChromaDefaultEmbedding()
    else:
        raise ValueError(f"Unknown embedding provider: {provider_type}")
