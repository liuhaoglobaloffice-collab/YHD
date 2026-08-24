"""
Tests for Document Processing
"""

import pytest

from src.knowledge.processing import (
    Chunker,
    ChunkType,
    DocumentProcessor,
)


class TestChunker:
    """Test Chunker"""

    def test_chunk_text(self):
        """Test text chunking"""
        chunker = Chunker(min_chunk_size=50, max_chunk_size=200)

        content = """
        This is the first paragraph.
        It contains some text.
        
        This is the second paragraph.
        It also contains text.
        
        This is the third paragraph.
        """

        chunks = chunker.chunk_text(
            document_id="doc1",
            document_version=1,
            content=content,
        )

        assert len(chunks) > 0
        assert all(chunk.document_id == "doc1" for chunk in chunks)
        assert all(chunk.document_version == 1 for chunk in chunks)

    def test_chunk_type_detection(self):
        """Test chunk type detection"""
        chunker = Chunker()

        # Heading
        assert chunker._detect_chunk_type("# Heading") == ChunkType.HEADING
        assert chunker._detect_chunk_type("## Subheading") == ChunkType.HEADING

        # List
        assert chunker._detect_chunk_type("- Item 1\n- Item 2") == ChunkType.LIST
        assert chunker._detect_chunk_type("* Item 1\n* Item 2") == ChunkType.LIST

        # Code
        assert chunker._detect_chunk_type("```python\ncode\n```") == ChunkType.CODE

        # Paragraph
        assert chunker._detect_chunk_type("Regular text") == ChunkType.PARAGRAPH

    def test_split_large_paragraph(self):
        """Test splitting large paragraphs"""
        chunker = Chunker(max_chunk_size=100)

        # Create a large paragraph
        paragraph = " ".join(["This is a sentence."] * 20)

        chunks = chunker._split_large_paragraph(paragraph)
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)


class TestDocumentProcessor:
    """Test DocumentProcessor"""

    @pytest.mark.asyncio
    async def test_process_text_document(self):
        """Test processing text document"""
        processor = DocumentProcessor()

        content = b"This is a test document.\n\nIt has multiple paragraphs.\n\nAnd some text."

        chunks = await processor.process_document(
            document_id="doc1",
            document_version=1,
            file_type="text/plain",
            content=content,
        )

        assert len(chunks) > 0
        assert all(chunk.document_id == "doc1" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_process_markdown_document(self):
        """Test processing markdown document"""
        processor = DocumentProcessor()

        content = b"# Heading\n\nSome content.\n\n## Subheading\n\nMore content."

        chunks = await processor.process_document(
            document_id="doc1",
            document_version=1,
            file_type="text/markdown",
            content=content,
        )

        assert len(chunks) > 0

    def test_clean_text(self):
        """Test text cleaning"""
        processor = DocumentProcessor()

        text = "This   has   excessive   spaces.\n\n\nAnd newlines."
        cleaned = processor._clean_text(text)

        assert "  " not in cleaned
        assert cleaned == "This has excessive spaces. And newlines."

    def test_normalize_text(self):
        """Test text normalization"""
        processor = DocumentProcessor()

        text = "\"curly quotes\" and 'single quotes' and - dashes"
        normalized = processor._normalize_text(text)

        assert '"' in normalized
        assert "'" in normalized
        assert "-" in normalized
