"""
S1 操作台资料导入 - 服务层

提供统一的批量资料导入能力（供应商/客户/合同/报价），
支持 Excel/CSV/PDF/Word/图片OCR 多格式解析、校验并落库，
同时写入导入任务记录（ImportRecord）。
"""

import io
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.imports.models import (
    Contract,
    Customer,
    ImportRecord,
    ImportStatus,
    ImportType,
    Quotation,
)
from src.business.imports.parser import (
    PDFParser,
    OCRParser,
    DocxParser,
    detect_file_format,
    parse_structured_table_from_text,
)

logger = structlog.get_logger(__name__)


class ImportService:
    """批量资料导入服务"""

    # 各导入类型的列映射（Excel/CSV 表头 -> 模型字段）
    COLUMN_MAPPINGS: Dict[str, Dict[str, str]] = {
        ImportType.CUSTOMER: {
            "客户名称": "name",
            "联系人": "name",
            "公司": "company",
            "公司名称": "company",
            "国家": "country",
            "城市": "city",
            "地址": "address",
            "电话": "phone",
            "邮箱": "email",
            "网站": "website",
            "微信": "wechat",
            "WhatsApp": "whatsapp",
            "感兴趣产品": "product_interest",
            "状态": "status",
            "来源": "source",
            "备注": "notes",
        },
        ImportType.CONTRACT: {
            "合同编号": "contract_no",
            "合同名称": "name",
            "客户名称": "customer_name",
            "供应商名称": "supplier_name",
            "金额": "amount",
            "币种": "currency",
            "开始日期": "start_date",
            "结束日期": "end_date",
            "状态": "status",
            "备注": "notes",
        },
        ImportType.QUOTATION: {
            "报价编号": "quotation_no",
            "报价名称": "name",
            "客户名称": "customer_name",
            "产品": "product",
            "单价": "unit_price",
            "数量": "quantity",
            "总金额": "amount",
            "币种": "currency",
            "有效期至": "valid_until",
            "状态": "status",
            "备注": "notes",
        },
    }

    # 日期字段
    DATE_FIELDS: Dict[str, List[str]] = {
        ImportType.CONTRACT: ["start_date", "end_date"],
        ImportType.QUOTATION: ["valid_until"],
    }

    # 必填字段
    REQUIRED_FIELDS: Dict[str, List[str]] = {
        ImportType.CUSTOMER: ["name"],
        ImportType.CONTRACT: ["contract_no"],
        ImportType.QUOTATION: ["quotation_no"],
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== 解析 ====================

    def parse_file(self, file_content: bytes, file_type: str = "excel") -> pd.DataFrame:
        """解析 Excel/CSV/PDF/图片/Word 文件为 DataFrame。

        支持格式：excel, csv, pdf, image, docx
        """
        if file_type == "csv":
            return pd.read_csv(io.BytesIO(file_content)).fillna("")
        elif file_type == "excel":
            return pd.read_excel(io.BytesIO(file_content)).fillna("")

        # 非结构化格式需要先用解析器提取文本，再尝试转表格
        text = self._parse_text(file_content, file_type)
        if not text:
            return pd.DataFrame()

        # 尝试从文本解析结构化表格
        rows = parse_structured_table_from_text(text)
        if rows:
            df = pd.DataFrame(rows)
            if not df.empty:
                return df.fillna("")

        # 无法解析为表格，每行作为一条记录
        return pd.DataFrame({"raw_text": [line for line in text.split("\n") if line.strip()]}).fillna("")

    def _parse_text(self, file_content: bytes, file_type: str) -> str:
        """将非结构化文件解析为纯文本。"""
        if file_type == "pdf":
            parser = PDFParser()
            if not parser.is_available():
                logger.warning("pdf_parser_not_available", hint="install pdfplumber")
                return ""
            result = parser.parse(file_content)
            return result.text if result.success else ""

        elif file_type == "image":
            parser = OCRParser()
            if not parser.is_available():
                logger.warning("ocr_parser_not_available", hint="install pytesseract")
                return ""
            result = parser.parse(file_content, lang="chi+eng")
            return result.text if result.success else ""

        elif file_type == "docx":
            parser = DocxParser()
            if not parser.is_available():
                logger.warning("docx_parser_not_available", hint="install python-docx")
                return ""
            result = parser.parse(file_content)
            return result.text if result.success else ""

        logger.warning("unsupported_file_type", file_type=file_type)
        return ""

    def _map_row(
        self, row: pd.Series, import_type: ImportType
    ) -> Dict[str, Any]:
        """将一行数据按列映射转换为模型字段。"""
        mapping = self.COLUMN_MAPPINGS.get(import_type, {})
        data: Dict[str, Any] = {}
        for col, value in row.items():
            field = mapping.get(str(col).strip())
            if not field or value in ("", None):
                continue
            data[field] = value
        return data

    def _cast_dates(self, data: Dict[str, Any], import_type: ImportType) -> Dict[str, Any]:
        """转换日期字段为 datetime。"""
        for field in self.DATE_FIELDS.get(import_type, []):
            value = data.get(field)
            if isinstance(value, str) and value:
                try:
                    data[field] = datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    data[field] = None
            elif value is None or value == "":
                data[field] = None
        return data

    # ==================== 供应商导入（复用现有模块） ====================

    async def _import_suppliers(
        self, file_content: bytes, file_type: str
    ) -> Dict[str, Any]:
        from src.business.supplier.import_export import SupplierImportExport

        importer = SupplierImportExport(self.session)
        result = await importer.import_suppliers(file_content, file_type=file_type)

        # 规范化错误格式：供应商导入返回 {index, errors/error}，统一为 {row, error}
        normalized_errors: List[Dict[str, Any]] = []
        for err in result.get("errors", []):
            row = err.get("index", 0) + 2  # 表头占第 1 行
            messages = err.get("errors") or err.get("error") or "导入失败"
            if isinstance(messages, str):
                messages = [messages]
            for message in messages:
                normalized_errors.append({"row": row, "error": str(message)})
        result["errors"] = normalized_errors
        return result

    # ==================== 客户/合同/报价导入 ====================

    async def _import_generic(
        self,
        file_content: bytes,
        file_type: str,
        import_type: ImportType,
    ) -> Dict[str, Any]:
        """解析并落库客户/合同/报价资料。"""
        try:
            df = self.parse_file(file_content, file_type)
        except Exception as e:  # noqa: BLE001
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"row": 0, "error": f"文件解析失败: {e}"}],
            }

        model_map = {
            ImportType.CUSTOMER: Customer,
            ImportType.CONTRACT: Contract,
            ImportType.QUOTATION: Quotation,
        }
        model = model_map[import_type]
        required = self.REQUIRED_FIELDS.get(import_type, [])

        success, failed, errors = 0, 0, []
        total = len(df)

        for index, row in df.iterrows():
            data = self._map_row(row, import_type)
            data = self._cast_dates(data, import_type)
            row_no = index + 2  # 表头占第 1 行

            # 必填字段校验
            missing = [f for f in required if not data.get(f)]
            if missing:
                failed += 1
                errors.append(
                    {"row": row_no, "error": f"缺少必填字段: {', '.join(missing)}"}
                )
                continue

            try:
                # 数值字段转换
                for num_field in ("amount", "unit_price"):
                    if num_field in data and data[num_field] not in (None, ""):
                        data[num_field] = float(data[num_field])
                if "quantity" in data and data["quantity"] not in (None, ""):
                    data["quantity"] = int(float(data["quantity"]))

                record = model(**data)
                self.session.add(record)
                await self.session.flush()
                success += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                errors.append({"row": row_no, "error": f"数据写入失败: {e}"})

        await self.session.commit()
        return {"total": total, "success": success, "failed": failed, "errors": errors}

    # ==================== 统一入口 ====================

    async def import_file(
        self,
        import_type: str,
        file_content: bytes,
        file_type: str = "excel",
        filename: str = "",
        created_by: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        统一批量导入入口。

        Returns:
            {"total": int, "success": int, "failed": int, "errors": List, "import_record_id": int}
        """
        import_type_enum = ImportType(import_type)
        record = ImportRecord(
            import_type=import_type_enum,
            filename=filename or "upload",
            file_type=file_type,
            status=ImportStatus.PROCESSING,
            created_by=created_by,
            tenant_id=tenant_id,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        try:
            if import_type_enum == ImportType.SUPPLIER:
                result = await self._import_suppliers(file_content, file_type)
            else:
                result = await self._import_generic(
                    file_content, file_type, import_type_enum
                )
        except Exception as e:  # noqa: BLE001
            logger.error("import_failed", import_type=import_type, error=str(e))
            result = {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"row": 0, "error": f"导入异常: {e}"}],
            }

        # 更新导入记录
        total = result.get("total")
        success = result.get("success", 0)
        failed = result.get("failed", 0)
        # 供应商导入结果不返回 total，用成功+失败补全
        if total is None:
            total = success + failed
        if failed == 0 and total > 0:
            status = ImportStatus.COMPLETED
        elif failed > 0 and success > 0:
            status = ImportStatus.PARTIAL
        else:
            status = ImportStatus.FAILED

        record.total = total
        record.success = success
        record.failed = failed
        record.status = status
        record.errors = result.get("errors", [])
        record.completed_at = datetime.now(UTC)
        await self.session.commit()

        result["import_record_id"] = record.id
        result["status"] = status.value
        logger.info(
            "import_completed",
            import_type=import_type,
            record_id=record.id,
            total=total,
            success=success,
            failed=failed,
        )
        return result

    # ==================== 查询 ====================

    async def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        import_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询导入记录。"""
        stmt = select(ImportRecord)
        if import_type:
            stmt = stmt.where(ImportRecord.import_type == ImportType(import_type))
        total_stmt = select(ImportRecord.id).where(stmt.whereclause or True)
        total = len(list((await self.session.execute(total_stmt)).scalars().all()))

        stmt = stmt.order_by(ImportRecord.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        records = list((await self.session.execute(stmt)).scalars().all())
        return {
            "items": [
                {
                    "id": r.id,
                    "import_type": r.import_type.value,
                    "filename": r.filename,
                    "file_type": r.file_type,
                    "status": r.status.value,
                    "total": r.total,
                    "success": r.success,
                    "failed": r.failed,
                    "errors": r.errors or [],
                    "created_by": r.created_by,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "completed_at": (
                        r.completed_at.isoformat() if r.completed_at else None
                    ),
                }
                for r in records
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """查询单条导入记录。"""
        stmt = select(ImportRecord).where(ImportRecord.id == record_id)
        r = (await self.session.execute(stmt)).scalar_one_or_none()
        if not r:
            return None
        return {
            "id": r.id,
            "import_type": r.import_type.value,
            "filename": r.filename,
            "file_type": r.file_type,
            "status": r.status.value,
            "total": r.total,
            "success": r.success,
            "failed": r.failed,
            "errors": r.errors or [],
            "created_by": r.created_by,
            "tenant_id": r.tenant_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }

    def build_template_csv(self, import_type: str) -> str:
        """生成导入模板 CSV 内容（表头 + 一行示例）。"""
        import_type_enum = ImportType(import_type)
        headers = list(self.COLUMN_MAPPINGS.get(import_type_enum, {}).keys())
        sample: List[str] = []
        for header in headers:
            field = self.COLUMN_MAPPINGS[import_type_enum][header]
            sample.append(self._sample_value(import_type_enum, field))
        lines = [",".join(headers), ",".join(sample)]
        return "\n".join(lines)

    @staticmethod
    def _sample_value(import_type: ImportType, field: str) -> str:
        samples = {
            (ImportType.CUSTOMER, "name"): "示例客户",
            (ImportType.CUSTOMER, "company"): "Example Co., Ltd.",
            (ImportType.CUSTOMER, "country"): "美国",
            (ImportType.CUSTOMER, "email"): "demo@example.com",
            (ImportType.CUSTOMER, "whatsapp"): "+1 555 000 0000",
            (ImportType.CONTRACT, "contract_no"): "HT-2026-001",
            (ImportType.CONTRACT, "name"): "年度采购合同",
            (ImportType.CONTRACT, "amount"): "10000",
            (ImportType.CONTRACT, "currency"): "USD",
            (ImportType.CONTRACT, "start_date"): "2026-01-01",
            (ImportType.CONTRACT, "end_date"): "2026-12-31",
            (ImportType.QUOTATION, "quotation_no"): "BJ-2026-001",
            (ImportType.QUOTATION, "name"): "产品报价单",
            (ImportType.QUOTATION, "product"): "示例产品",
            (ImportType.QUOTATION, "unit_price"): "99.9",
            (ImportType.QUOTATION, "quantity"): "100",
            (ImportType.QUOTATION, "amount"): "9990",
        }
        return samples.get((import_type, field), "")
