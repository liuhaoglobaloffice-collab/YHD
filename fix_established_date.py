#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 established_date 序列化"""

def main():
    filepath = r"src/api/routes/supplier.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 将 established_date=supplier.established_date, 替换为转换后的版本
    replacements = [
        ('established_date=supplier.established_date,', 
         'established_date=supplier.established_date.isoformat() if supplier.established_date else None,'),
        ('established_date=s.established_date,', 
         'established_date=s.established_date.isoformat() if s.established_date else None,'),
        ('established_date=updated.established_date,', 
         'established_date=updated.established_date.isoformat() if updated.established_date else None,'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK - established_date 序列化已修复")

if __name__ == '__main__':
    main()
