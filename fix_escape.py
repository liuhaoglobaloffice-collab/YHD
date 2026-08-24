#!/usr/bin/env python3
"""修复测试文件中的转义字符问题"""

with open("tests/integration/test_supplier_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# 修复转义问题
content = content.replace("\\'", "'")

with open("tests/integration/test_supplier_api.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed")
