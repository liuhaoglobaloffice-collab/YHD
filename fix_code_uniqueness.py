#!/usr/bin/env python3
"""完全修复测试数据唯一性 - 使用完整时间戳"""

import re

with open('tests/integration/test_supplier_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修改所有 code 为使用完整时间戳（14位）
content = re.sub(
    r'"code": f"SUP(\d{4})\{timestamp\[:8\]\}",',
    r'"code": f"SUP\1-{timestamp}",',
    content
)

with open('tests/integration/test_supplier_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed code uniqueness")
