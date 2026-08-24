#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除 business_scope 字段"""

def main():
    filepath = r"src/api/routes/supplier.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 过滤掉包含 business_scope 的行
    filtered_lines = []
    for line in lines:
        if 'business_scope' in line:
            print(f"删除: {line.rstrip()}")
            continue
        filtered_lines.append(line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)
    
    print(f"\nOK - 已删除 {len(lines) - len(filtered_lines)} 行")

if __name__ == '__main__':
    main()
