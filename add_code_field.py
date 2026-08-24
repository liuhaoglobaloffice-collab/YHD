#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 SupplierResponse 构造中添加 code 字段"""

import re

def main():
    filepath = r"src/api/routes/supplier.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 name= 后面添加 code=
    # 匹配模式：name=supplier.name, 或 name=s.name, 或 name=updated.name,
    pattern = r'(\s+name=(?:supplier|s|updated)\.name,)\n'
    replacement = r'\1\n        code=\g<1>.replace("name", "code"),\n'
    
    # 更精确的替换
    patterns = [
        (r'(\s+name=supplier\.name,)\n', r'\1\n        code=supplier.code,\n'),
        (r'(\s+name=s\.name,)\n', r'\1\n            code=s.code,\n'),
        (r'(\s+name=updated\.name,)\n', r'\1\n        code=updated.code,\n'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK - 已添加 code 字段到所有响应")

if __name__ == '__main__':
    main()
