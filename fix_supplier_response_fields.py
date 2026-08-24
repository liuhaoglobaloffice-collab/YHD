#!/usr/bin/env python3
"""修复 SupplierResponse 缺少必填字段"""

with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在 get_supplier 的 SupplierResponse 中添加缺失字段
# 找到 business_type=supplier.business_type, 这一行，在其后添加
content = content.replace(
    '        business_type=supplier.business_type,\n        country=supplier.country,',
    '        business_type=supplier.business_type.value,\n        status=supplier.status.value,\n        industry=supplier.industry,\n        website=supplier.website,\n        description=supplier.description,\n        country=supplier.country,'
)

# 移除重复的 website
content = content.replace(
    '        country=supplier.country,\n        province=supplier.province,\n        city=supplier.city,\n        address=supplier.address,\n        website=supplier.website,',
    '        country=supplier.country,\n        province=supplier.province,\n        city=supplier.city,\n        address=supplier.address,'
)

# 同样修复 update_supplier 路由
content = content.replace(
    '        business_type=updated_supplier.business_type,\n        country=updated_supplier.country,',
    '        business_type=updated_supplier.business_type.value,\n        status=updated_supplier.status.value,\n        industry=updated_supplier.industry,\n        website=updated_supplier.website,\n        description=updated_supplier.description,\n        country=updated_supplier.country,'
)

# 移除update中重复的website
content = content.replace(
    '        country=updated_supplier.country,\n        province=updated_supplier.province,\n        city=updated_supplier.city,\n        address=updated_supplier.address,\n        website=updated_supplier.website,',
    '        country=updated_supplier.country,\n        province=updated_supplier.province,\n        city=updated_supplier.city,\n        address=updated_supplier.address,'
)

with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed SupplierResponse fields")
