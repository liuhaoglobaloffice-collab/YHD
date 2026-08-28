"""
产品目录管理 API 路由

提供产品 CRUD 操作，归属当前用户/租户。
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.database.models import ProductModel
from src.identity.models import User

router = APIRouter(prefix="/products", tags=["products"])


# ==================== Schemas ====================


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = "件"
    moq: Optional[int] = None
    image_url: Optional[str] = None
    tags: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    moq: Optional[int] = None
    image_url: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None


class ProductOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    moq: Optional[int] = None
    image_url: Optional[str] = None
    status: str
    tags: Optional[str] = None
    created_at: str
    updated_at: str


def _to_out(product: ProductModel) -> Dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "price": product.price,
        "unit": product.unit or "件",
        "moq": product.moq,
        "image_url": product.image_url,
        "status": product.status,
        "tags": product.tags,
        "created_at": product.created_at.isoformat() if product.created_at else "",
        "updated_at": product.updated_at.isoformat() if product.updated_at else "",
    }


# ==================== Routes ====================


@router.get("")
async def list_products(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(active|inactive)$"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取产品列表（分页、筛选、搜索）。"""
    query = select(ProductModel)

    # 归属过滤（Tenant 隔离 + 数据范围）
    from src.identity.visibility import DataScopeFilter
    scope_filter = DataScopeFilter(current_user)
    query = scope_filter.apply_to_query(
        query, ProductModel, owner_field="created_by", user_id_field="created_by"
    )

    if category:
        query = query.where(ProductModel.category == category)
    if status:
        query = query.where(ProductModel.status == status)
    if search:
        like = f"%{search}%"
        query = query.where(
            ProductModel.name.ilike(like) | ProductModel.description.ilike(like)
        )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one() or 0

    # 分页
    query = query.order_by(desc(ProductModel.updated_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = list((await session.execute(query)).scalars().all())

    return {
        "items": [_to_out(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取单个产品详情。"""
    product = await session.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return _to_out(product)


@router.post("", status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """创建新产品。"""
    product = ProductModel(
        name=data.name,
        category=data.category,
        description=data.description,
        price=data.price,
        unit=data.unit or "件",
        moq=data.moq,
        image_url=data.image_url,
        tags=data.tags,
        status="active",
        created_by=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return _to_out(product)


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """更新产品信息。"""
    product = await session.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return _to_out(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """删除产品。"""
    product = await session.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    await session.delete(product)
    await session.commit()
    return {"status": "deleted", "id": product_id}