#!/usr/bin/env python3
"""移动 batch 路由到 /{supplier_id} 之前"""

# 读取文件
with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 提取 batch 路由 (行774-816, 索引773-815)
batch_routes = lines[773:816]

# 删除原位置的 batch 路由
lines_without_batch = lines[:773] + lines[816:]

# 找到插入位置：在行267 (索引266) 之前插入
insert_index = 266

# 插入 batch 路由
new_lines = lines_without_batch[:insert_index] + batch_routes + lines_without_batch[insert_index:]

# 写回文件
with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Batch routes moved successfully')
