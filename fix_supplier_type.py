#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本：替换 supplier_type → business_type"""

import os

def replace_in_file(filepath, old_text, new_text):
    """替换文件中的文本"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_count = content.count(old_text)
        content = content.replace(old_text, new_text)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"OK {filepath} - 替换 {original_count} 处")
        return True
    except Exception as e:
        print(f"ERROR {filepath}: {e}")
        return False

def main():
    base_dir = r"D:\LiuHao-AI-OS"
    os.chdir(base_dir)
    
    # 1. API routes: supplier_type → business_type
    replace_in_file(
        'src/api/routes/supplier.py',
        'supplier_type',
        'business_type'
    )
    
    # 2. 测试文件: "supplier_type" → "business_type"
    replace_in_file(
        'tests/integration/test_supplier_api.py',
        '"supplier_type"',
        '"business_type"'
    )
    
    print("\n=== 替换完成 ===")

if __name__ == '__main__':
    main()
