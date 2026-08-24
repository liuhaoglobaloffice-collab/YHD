#!/usr/bin/env python3
"""修复 list_suppliers_api 的 code 唯一性"""

with open('tests/integration/test_supplier_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 list test 中的 code，在末尾添加 {i}
content = content.replace(
    '"code": f"SUP610{i}{timestamp[:8]}",',
    '"code": f"SUP610{i}-{timestamp}",  # 使用完整时间戳+索引'
)

# 同样修复 advanced search test
content = content.replace(
    '"code": f"SUP700{i}{timestamp[:8]}",',
    '"code": f"SUP700{i}-{timestamp}",  # 使用完整时间戳+索引'
)

# 还有一些遗漏的地方 - 修复所有 [:8] 的情况
import re
content = re.sub(
    r'"code": f"SUP(\d+)\{timestamp\[:8\]\}",',
    r'"code": f"SUP\1-{timestamp}",',
    content
)

with open('tests/integration/test_supplier_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed list_suppliers code uniqueness")
