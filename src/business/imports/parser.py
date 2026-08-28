"""
资料导入 - 多格式文件解析器扩展

支持解析更多文件格式：
- PDF 文本提取
- 图片 OCR 文本提取（需要 pytesseract + pillow）
- Word 文档 (.docx)
"""

import io
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    text: str = ""
    tables: Optional[List[List[Dict[str, Any]]]] = None
    error: str = ""
    page_count: int = 1


class PDFParser:
    """PDF 文件文本和表格解析"""

    def __init__(self):
        self._has_pdfplumber = False
        self._has_pypdf = False
        try:
            import pdfplumber
            self._has_pdfplumber = True
        except ImportError:
            try:
                from pypdf import PdfReader
                self._has_pypdf = True
            except ImportError:
                pass

    def is_available(self) -> bool:
        """检查是否有PDF解析库可用"""
        return self._has_pdfplumber or self._has_pypdf

    def parse(self, file_content: bytes) -> ParseResult:
        """解析PDF，提取文本和表格。"""
        if not self.is_available():
            return ParseResult(
                success=False,
                error="PDF解析库未安装，请安装 pdfplumber 或 pypdf"
            )

        try:
            text = ""
            tables: List[List[Dict[str, Any]]] = []

            if self._has_pdfplumber:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                        # 提取表格
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            # 简化处理：第一行是表头，转成字典列表
                            if len(table) > 1 and table[0]:
                                headers = [cell if cell else f"col_{i}" for i, cell in enumerate(table[0])]
                for row in table[1:]:
                                    row_dict = {}
                                    for i, cell in enumerate(row):
                                        if i < len(headers):
                                            row_dict[headers[i]] = cell
                                    tables.append(row_dict)
            elif self._has_pypdf:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_content))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

            return ParseResult(
                success=True,
                text=text.strip(),
                tables=tables if tables else None,
                page_count=len(reader.pages) if 'reader' in locals() else 1,
            )

        except Exception as e:
            logger.error("pdf_parse_failed", error=str(e))
            return ParseResult(
                success=False,
                error=f"PDF解析失败: {str(e)}"
            )


class OCRParser:
    """图片文件 OCR 文本解析（需要 pytesseract）"""

    def __init__(self):
        self._available = False
        try:
            import pytesseract
            from PIL import Image
            self._pytesseract = pytesseract
            self._Image = Image
            self._available = True
        except ImportError:
            pass

    def is_available(self) -> bool:
        """检查OCR是否可用"""
        return self._available

    def parse(self, file_content: bytes, lang: str = "chi+eng") -> ParseResult:
        """从图片中OCR提取文本。

        Args:
            file_content: 图片字节
            lang: 语言代码，chi 中文，eng 英文，chi+eng 中英混合
        """
        if not self.is_available():
            return ParseResult(
                success=False,
                error="OCR库未安装，请安装 pytesseract 和 pillow"
            )

        try:
            image = self._Image.open(io.BytesIO(file_content))
            text = self._pytesseract.image_to_string(image, lang=lang)

            return ParseResult(
                success=True,
                text=text.strip(),
            )
        except Exception as e:
            logger.error("ocr_parse_failed", error=str(e))
            return ParseResult(
                success=False,
                error=f"OCR解析失败: {str(e)}"
            )


class DocxParser:
    """Word 文档 (.docx) 文本解析"""

    def __init__(self):
        self._available = False
        try:
            from docx import Document
            self._Document = Document
            self._available = True
        except ImportError:
            pass

    def is_available(self) -> bool:
        """检查docx解析是否可用"""
        return self._available

    def parse(self, file_content: bytes) -> ParseResult:
        """解析docx提取文本。"""
        if not self.is_available():
            return ParseResult(
                success=False,
                error="python-docx 未安装，请安装 python-docx"
            )

        try:
            doc = self._Document(io.BytesIO(file_content))
            text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return ParseResult(
                success=True,
                text=text.strip(),
            )
        except Exception as e:
            logger.error("docx_parse_failed", error=str(e))
            return ParseResult(
                success=False,
                error=f"Word文档解析失败: {str(e)}"
            )


def detect_file_format(filename: str, content_type: Optional[str] = None) -> str:
    """根据文件名或Content-Type检测文件格式。

    Returns:
        excel | csv | pdf | image | docx | unknown
    """
    name_lower = filename.lower()

    if name_lower.endswith((".xlsx", ".xls", ".xlsm")):
        return "excel"
    if name_lower.endswith((".csv", ".tsv")):
        return "csv"
    if name_lower.endswith((".pdf")):
        return "pdf"
    if name_lower.endswith((".docx")):
        return "docx"
    if name_lower.endswith((".doc")):
        return "doc"  # .doc 不支持
    if name_lower.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif")):
        return "image"

    # 检查 Content-Type
    if content_type:
        ct = content_type.lower()
        if "pdf" in ct:
            return "pdf"
        if "image" in ct:
            return "image"
        if "excel" in ct or "spreadsheet" in ct:
            return "excel"
        if "csv" in ct or "text/csv" in ct:
            return "csv"
        if "word" in ct or "docx" in ct:
            return "docx"

    return "unknown"


def parse_structured_table_from_text(
    text: str,
    has_header: bool = True,
) -> List[Dict[str, Any]]:
    """从纯文本中尝试解析表格（启发式）。

    用于PDF扫描件或图片OCR后得到的文本尝试转表格。
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return []

    result: List[Dict[str, Any]] = []
    headers: List[str] = []

    # 尝试检测制表符或多个空格分隔
    if has_header and len(lines) > 0:
        first_line = lines[0]
        # 如果有制表符，按制表符分割
        if "\t" in first_line:
            headers = [h.strip() for h in first_line.split("\t") if h.strip()]
            for line in lines[1:]:
                cells = [c.strip() for c in line.split("\t") if c.strip()]
                row: Dict[str, Any] = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row[headers[i]] = cell
                result.append(row)
            return result
        # 如果有多个连续空格，尝试按空格分割（简单处理）
        elif re.search(r"\s{3,}", first_line):
            parts = re.split(r"\s{3,}", first_line)
            headers = [p.strip() for p in parts if p.strip()]
            for line in lines[1:]:
                cells = re.split(r"\s{3,}", line.strip())
                cells = [p.strip() for p in cells if p.strip()]
                row: Dict[str, Any] = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row[headers[i]] = cell
                result.append(row)
            return result

    # 无法解析结构化表格，返回每行作为一条记录单列
    return [{"raw_text": line} for line in lines]
