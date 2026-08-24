#!/usr/bin/env python3
"""添加缺失的 batch 路由"""

# 读取文件
with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到插入位置：在 /advanced-search 之后，/{supplier_id} 之前
marker = '@router.get("/{supplier_id}", response_model=SupplierResponse)'
insert_pos = content.find(marker)

if insert_pos < 0:
    print("ERROR: Cannot find /{supplier_id} route")
    exit(1)

# 准备 batch 路由代码
batch_routes = '''

@router.post("/batch", status_code=201)
async def batch_create_suppliers(
    suppliers: List[SupplierCreateRequest],
    validate: bool = True,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "create")),
):
    """批量创建供应商"""
    crud_instance = crud(session)
    suppliers_data = [s.model_dump() for s in suppliers]
    result = await crud_instance.batch_create(suppliers_data, validate=validate)
    return result


@router.put("/batch")
async def batch_update_suppliers(
    updates: List[dict],
    validate: bool = True,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "update")),
):
    """批量更新供应商"""
    crud_instance = crud(session)
    result = await crud_instance.batch_update(updates, validate=validate)
    return result


@router.delete("/batch")
async def batch_delete_suppliers(
    supplier_ids: List[int],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("supplier", "delete")),
):
    """批量删除供应商"""
    crud_instance = crud(session)
    result = await crud_instance.batch_delete(supplier_ids)
    return result

'''

# 在 /{supplier_id} 之前插入
content = content[:insert_pos] + batch_routes + content[insert_pos:]

# 写回文件
with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully added batch routes:")
print("  - POST /batch")
print("  - PUT /batch")
print("  - DELETE /batch")
