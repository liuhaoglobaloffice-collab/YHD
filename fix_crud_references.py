#!/usr/bin/env python3
"""修复所有 crud 未定义的问题"""

import re

# 读取文件
with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有 `crud_instance = crud(session)` 为 `crud = SupplierCRUD(session)`
content = content.replace('crud_instance = crud(session)', 'crud = SupplierCRUD(session)')

# 替换所有 `crud_instance.` 为 `crud.`
content = content.replace('crud_instance.', 'crud.')

# 写回文件
with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all crud references")
