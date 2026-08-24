#!/usr/bin/env python3
"""添加分页响应模型"""

with open("src/api/routes/supplier.py", "r", encoding="utf-8") as f:
    content = f.read()

# 在 RiskAssessmentTriggerRequest 之前插入新类
insert_point = content.find('class RiskAssessmentTriggerRequest')
if insert_point > 0:
    new_class = """class SupplierListResponse(BaseModel):
    \"\"\"供应商列表分页响应\"\"\"
    items: List[SupplierResponse]
    total: int


"""
    content = content[:insert_point] + new_class + content[insert_point:]
    
    # 修改路由定义
    content = content.replace(
        '@router.get("", response_model=List[SupplierResponse])',
        '@router.get("", response_model=SupplierListResponse)'
    )
    
    with open("src/api/routes/supplier.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Added SupplierListResponse and updated route")
else:
    print("✗ Not found")
