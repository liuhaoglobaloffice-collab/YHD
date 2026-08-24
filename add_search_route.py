#!/usr/bin/env python3
"""添加 /search 路由"""

with open("src/api/routes/supplier.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到 /advanced-search 路由所在行
insert_line = None
for i, line in enumerate(lines):
    if '@router.get("/advanced-search")' in line:
        insert_line = i
        break

if insert_line:
    # 在 advanced-search 之前插入 search 路由
    search_route = '''@router.get("/search")
async def search_suppliers(
    query: str = Query(..., description="搜索关键词"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """
    简单搜索供应商（按名称）
    
    需要权限: supplier:read
    """
    from sqlalchemy import select, or_
    from src.business.supplier.models import Supplier
    
    # 模糊搜索名称或法定名称
    stmt = select(Supplier).where(
        or_(
            Supplier.name.ilike(f"%{query}%"),
            Supplier.legal_name.ilike(f"%{query}%")
        )
    ).limit(100)
    
    result = await session.execute(stmt)
    suppliers = result.scalars().all()
    
    return [
        SupplierResponse(
            id=s.id,
            name=s.name,
            code=s.code,
            legal_name=s.legal_name,
            business_type=s.business_type.value,
            status=s.status.value,
            industry=s.industry,
            website=s.website,
            description=s.description,
            address=s.address,
            phone=s.phone,
            email=s.email,
            registered_capital=s.registered_capital,
            established_date=s.established_date.isoformat() if s.established_date else None,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in suppliers
    ]


'''
    lines.insert(insert_line, search_route)
    
    with open("src/api/routes/supplier.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Added /search route")
else:
    print("Could not find insertion point")
