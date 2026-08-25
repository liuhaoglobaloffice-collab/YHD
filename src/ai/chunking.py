"""
文档分块工具
Week 4 Day 4 - RAG基础实现

功能：
1. 递归字符分割
2. 保留上下文重叠
3. 元数据传递
"""

from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


class TextChunk:
    """文本块数据结构"""

    def __init__(
        self,
        text: str,
        metadata: Optional[dict] = None,
        chunk_index: int = 0,
        total_chunks: int = 1,
    ):
        self.text = text
        self.metadata = metadata or {}
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks

        # 添加分块信息到元数据
        self.metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "chunk_length": len(text),
            }
        )

    def __repr__(self) -> str:
        return f"TextChunk(index={self.chunk_index}/{self.total_chunks}, length={len(self.text)})"


class RecursiveCharacterTextSplitter:
    """
    递归字符文本分割器

    按照优先级尝试多种分隔符，确保文本在合理边界分割
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
    ):
        """
        初始化分割器

        Args:
            chunk_size: 每块最大字符数
            chunk_overlap: 块之间重叠字符数
            separators: 分隔符列表（优先级从高到低）
            keep_separator: 是否保留分隔符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.keep_separator = keep_separator

        # 默认分隔符：段落 > 句子 > 短语 > 单词 > 字符
        self.separators = separators or [
            "\n\n",  # 段落
            "\n",  # 行
            "。",  # 中文句号
            "！",  # 中文感叹号
            "？",  # 中文问号
            "；",  # 中文分号
            "，",  # 中文逗号
            ". ",  # 英文句号+空格
            "! ",  # 英文感叹号+空格
            "? ",  # 英文问号+空格
            "; ",  # 英文分号+空格
            ", ",  # 英文逗号+空格
            " ",  # 空格
            "",  # 字符
        ]

        logger.info(
            "text_splitter_initialized",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators_count=len(self.separators),
        )

    def split_text(self, text: str, metadata: Optional[dict] = None) -> List[TextChunk]:
        """
        分割文本

        Args:
            text: 输入文本
            metadata: 原始文档元数据

        Returns:
            文本块列表
        """
        if not text:
            return []

        # 去除首尾空白
        text = text.strip()

        # 如果文本小于chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [TextChunk(text=text, metadata=metadata, chunk_index=0, total_chunks=1)]

        # 递归分割
        chunks_text = self._recursive_split(text, self.separators)

        # 合并小块和处理重叠
        merged_chunks = self._merge_and_overlap(chunks_text)

        # 创建 TextChunk 对象
        total_chunks = len(merged_chunks)
        chunks = [
            TextChunk(
                text=chunk_text,
                metadata=metadata,
                chunk_index=i,
                total_chunks=total_chunks,
            )
            for i, chunk_text in enumerate(merged_chunks)
        ]

        logger.info(
            "text_split_complete",
            original_length=len(text),
            chunks_count=total_chunks,
            avg_chunk_size=sum(len(c.text) for c in chunks) // total_chunks if chunks else 0,
        )

        return chunks

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """
        递归分割文本

        Args:
            text: 文本
            separators: 当前可用分隔符列表

        Returns:
            分割后的文本列表
        """
        # 没有分隔符或文本足够小，直接返回
        if not separators or len(text) <= self.chunk_size:
            return [text]

        # 取第一个分隔符
        separator = separators[0]
        remaining_separators = separators[1:]

        # 尝试用当前分隔符分割
        if separator == "":
            # 最后兜底：按字符分割
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        splits = text.split(separator)

        # 如果保留分隔符，将其重新附加
        if self.keep_separator and separator:
            splits = [
                (split + separator if i < len(splits) - 1 else split)
                for i, split in enumerate(splits)
            ]

        # 递归处理每个片段
        final_chunks = []
        for split in splits:
            if len(split) > self.chunk_size:
                # 片段仍然太大，用下一级分隔符继续分割
                sub_chunks = self._recursive_split(split, remaining_separators)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(split)

        return final_chunks

    def _merge_and_overlap(self, chunks: List[str]) -> List[str]:
        """
        合并过小的块并添加重叠

        Args:
            chunks: 初步分割的文本块列表

        Returns:
            合并并添加重叠后的文本块
        """
        if not chunks:
            return []

        merged = []
        current_chunk = ""

        for chunk in chunks:
            # 跳过空块
            if not chunk.strip():
                continue

            # 如果当前块为空，直接赋值
            if not current_chunk:
                current_chunk = chunk
                continue

            # 如果合并后不超过 chunk_size，继续合并
            if len(current_chunk) + len(chunk) <= self.chunk_size:
                current_chunk += chunk
            else:
                # 保存当前块
                merged.append(current_chunk)

                # 计算重叠部分
                if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap :]
                    current_chunk = overlap_text + chunk
                else:
                    current_chunk = chunk

        # 添加最后一块
        if current_chunk.strip():
            merged.append(current_chunk)

        return merged


class SimpleTextSplitter:
    """
    简单文本分割器

    按固定大小分割，不考虑语义边界
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化分割器

        Args:
            chunk_size: 每块字符数
            chunk_overlap: 重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str, metadata: Optional[dict] = None) -> List[TextChunk]:
        """
        分割文本

        Args:
            text: 输入文本
            metadata: 元数据

        Returns:
            文本块列表
        """
        if not text:
            return []

        chunks_text = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            if chunk.strip():
                chunks_text.append(chunk)

            start += self.chunk_size - self.chunk_overlap

        total_chunks = len(chunks_text)
        chunks = [
            TextChunk(
                text=chunk_text,
                metadata=metadata,
                chunk_index=i,
                total_chunks=total_chunks,
            )
            for i, chunk_text in enumerate(chunks_text)
        ]

        logger.info(
            "simple_split_complete",
            original_length=len(text),
            chunks_count=total_chunks,
        )

        return chunks
