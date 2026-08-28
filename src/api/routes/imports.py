"""
S1 操作台资料导入 API.

提供统一的批量资料导入端点（供应商/客户/合同/报价），
支持 Excel/CSV/PDF/Word/图片OCR 多格式自动检测与解析，
以及导入历史查询与模板下载。
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.business.imports.models import ImportType
from src.business.imports.service import ImportService
from src.business.imports.parser import detect_file_format
from src.identity.audit import AuditService
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/imports", tags=["imports"])

# 文件类型与格式说明
SUPPORTED_FORMATS = {
    "excel": [".xlsx", ".xls", ".xlsm"],
    "csv": [".csv", ".tsv"],
    "pdf": [".pdf"],
    "image": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"],
    "docx": [".docx"],
}


@router.post("/upload")
async def upload_import(
    import_type: str = Form(...),
    file: UploadFile = File(...),
    file_type: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("import", "create")),
):
    """
    批量导入资料（供应商/客户/合同/报价）。

    支持格式:
    - Excel (.xlsx, .xls, .xlsm)
    - CSV (.csv, .tsv)
    - PDF (.pdf) — 文本提取
    - 图片 (.jpg, .png, .bmp, .tiff) — OCR 识别
    - Word (.docx) — 文本提取

    - import_type: supplier | customer | contract | quotation
    - file: 导入文件
    - file_type: 可选，自动从文件名检测（excel/csv/pdf/image/docx）
    """
    if import_type not in [t.value for t in ImportType]:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的导入类型: {import_type}，可选: {[t.value for t in ImportType]}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    # 自动检测文件格式（如果未指定）
    if not file_type:
        file_type = detect_file_format(file.filename or "upload")
        if file_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"无法识别的文件格式: {file.filename}，支持: Excel/CSV/PDF/Word/图片"
            )
        logger.info("file_format_detected", filename=file.filename, detected=file_type)

    service = ImportService(session)
    result = await service.import_file(
        import_type=import_type,
        file_content=content,
        file_type=file_type,
        filename=file.filename or "upload",
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    await AuditService.log_success(
        session=session,
        action="import_data",
        resource_type="import",
        user_id=current_user.id,
        resource_id=str(result.get("import_record_id", "")),
        details={
            "import_type": import_type,
            "filename": file.filename,
            "file_type": file_type,
            "total": result.get("total"),
            "success": result.get("success"),
            "failed": result.get("failed"),
        },
    )

    return result


@router.get("")
async def list_imports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    import_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("import", "read")),
):
    """分页查询导入历史记录。"""
    service = ImportService(session)
    return await service.list_records(
        page=page, page_size=page_size, import_type=import_type
    )


@router.get("/templates/{import_type}")
async def get_import_template(
    import_type: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("import", "read")),
):
    """下载指定类型的导入模板（CSV）。"""
    if import_type not in [t.value for t in ImportType]:
        raise HTTPException(status_code=400, detail=f"不支持的导入类型: {import_type}")

    service = ImportService(session)
    csv_content = service.build_template_csv(import_type)
    filename = f"{import_type}_import_template.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{import_id}")
async def get_import_detail(
    import_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("import", "read")),
):
    """查询单条导入记录详情。"""
    service = ImportService(session)
    record = await service.get_record(import_id)
    if not record:
        raise HTTPException(status_code=404, detail="导入记录不存在")
    return record
