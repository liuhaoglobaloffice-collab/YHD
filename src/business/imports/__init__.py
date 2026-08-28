"""
S1 操作台资料导入（Import Intelligence）

提供供应商/客户/合同/报价的批量导入能力。
支持 10+ 种格式：Excel/CSV/PDF/Word/图片OCR
"""

from .models import (
    Contract,
    Customer,
    ImportRecord,
    ImportStatus,
    ImportType,
    Quotation,
)
from .service import ImportService
from .parser import (
    PDFParser,
    OCRParser,
    DocxParser,
    detect_file_format,
    ParseResult,
)

__all__ = [
    "Contract",
    "Customer",
    "ImportRecord",
    "ImportService",
    "ImportStatus",
    "ImportType",
    "Quotation",
    "PDFParser",
    "OCRParser",
    "DocxParser",
    "detect_file_format",
    "ParseResult",
]
