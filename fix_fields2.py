#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除 API routes 中不存在于数据库的字段"""

import re

def main():
    filepath = r"src/api/routes/supplier.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 过滤掉包含这三个字段的行
    filtered_lines = []
    for line in lines:
        if any(field in line for field in ['registration_number', 'tax_id', 'legal_representative']):
            print(f"删除: {line.rstrip()}")
            continue
        filtered_lines.append(line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)
    
    print(f"\nOK - 已删除 {len(lines) - len(filtered_lines)} 行")

if __name__ == '__main__':
    main()
