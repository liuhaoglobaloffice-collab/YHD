#!/usr/bin/env python3
"""添加缺失的 /{supplier_id} CRUD 路由"""

# 读取文件
with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到插入位置：在 /advanced-search 之后，/batch 或 /risk-history 之前
insert_marker = '@router.get("/advanced-search")'
insert_pos = content.find(insert_marker)

if insert_pos < 0:
    print("ERROR: Cannot find /advanced-search route")
    exit(1)

# 找到这个函数的结束位置（下一个 @router 之前）
next_router_pos = content.find('\n@router.', insert_pos + len(insert_marker))

if next_router_pos < 0:
    print("ERROR: Cannot find next router after /advanced-search")
    exit(1)

# 准备要插入的路由代码
missing_routes = '''

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "read")),
):
    """获取单个供应商详情"""
    crud_instance = crud(session)
    supplier = await crud_instance.get_supplier(supplier_id)
    
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    return SupplierResponse(
        id=supplier.id,
        code=supplier.code,
        name=supplier.name,
        legal_name=supplier.legal_name,
        business_type=supplier.business_type,
        country=supplier.country,
        province=supplier.province,
        city=supplier.city,
        address=supplier.address,
        website=supplier.website,
        email=supplier.email,
        phone=supplier.phone,
        registered_capital=supplier.registered_capital,
        established_date=supplier.established_date.isoformat() if supplier.established_date else None,
        employee_count=supplier.employee_count,
        annual_revenue=supplier.annual_revenue,
        main_products=supplier.main_products,
        certifications=supplier.certifications,
        payment_terms=supplier.payment_terms,
        credit_rating=supplier.credit_rating,
        cooperation_status=supplier.cooperation_status,
        data_source=supplier.data_source,
        notes=supplier.notes,
        is_active=supplier.is_active,
        created_at=supplier.created_at.isoformat(),
        updated_at=supplier.updated_at.isoformat(),
    )


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    update_data: SupplierUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """更新供应商信息"""
    crud_instance = crud(session)
    
    # 检查供应商是否存在
    existing_supplier = await crud_instance.get_supplier(supplier_id)
    if not existing_supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 执行更新
    updated_supplier = await crud_instance.update_supplier(
        supplier_id=supplier_id,
        **update_data.model_dump(exclude_unset=True)
    )
    
    return SupplierResponse(
        id=updated_supplier.id,
        code=updated_supplier.code,
        name=updated_supplier.name,
        legal_name=updated_supplier.legal_name,
        business_type=updated_supplier.business_type,
        country=updated_supplier.country,
        province=updated_supplier.province,
        city=updated_supplier.city,
        address=updated_supplier.address,
        website=updated_supplier.website,
        email=updated_supplier.email,
        phone=updated_supplier.phone,
        registered_capital=updated_supplier.registered_capital,
        established_date=updated_supplier.established_date.isoformat() if updated_supplier.established_date else None,
        employee_count=updated_supplier.employee_count,
        annual_revenue=updated_supplier.annual_revenue,
        main_products=updated_supplier.main_products,
        certifications=updated_supplier.certifications,
        payment_terms=updated_supplier.payment_terms,
        credit_rating=updated_supplier.credit_rating,
        cooperation_status=updated_supplier.cooperation_status,
        data_source=updated_supplier.data_source,
        notes=updated_supplier.notes,
        is_active=updated_supplier.is_active,
        created_at=updated_supplier.created_at.isoformat(),
        updated_at=updated_supplier.updated_at.isoformat(),
    )


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "delete")),
):
    """删除供应商"""
    crud_instance = crud(session)
    
    # 检查供应商是否存在
    existing_supplier = await crud_instance.get_supplier(supplier_id)
    if not existing_supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 执行删除
    await crud_instance.delete_supplier(supplier_id)
    return None

'''

# 在 next_router_pos 之前插入
content = content[:next_router_pos] + missing_routes + content[next_router_pos:]

# 写回文件
with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully added missing CRUD routes:")
print("  - GET /{supplier_id}")
print("  - PUT /{supplier_id}")
print("  - DELETE /{supplier_id}")
