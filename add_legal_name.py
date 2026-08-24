#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在所有响应构造中添加 legal_name 字段"""

import re

def main():
    filepath = r"src/api/routes/supplier.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 code= 后添加 legal_name=
    patterns = [
        (r'(        code=supplier\.code,)\n', r'\1\n        legal_name=supplier.legal_name,\n'),
        (r'(            code=s\.code,)\n', r'\1\n            legal_name=s.legal_name,\n'),
        (r'(        code=updated\.code,)\n', r'\1\n        legal_name=updated.legal_name,\n'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK - 已添加 legal_name 字段")

if __name__ == '__main__':
    main()
