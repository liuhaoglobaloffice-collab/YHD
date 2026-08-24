#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 supplier.py 所有语法错误"""

def main():
    filepath = r"src/api/routes/supplier.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 修复所有被合并的行
    fixed_lines = []
    for i, line in enumerate(lines):
        # 检查是否有两个字段定义在同一行
        if 'email:' in line and 'registered_capital:' in line:
            # 分割成两行
            parts = line.split('    registered_capital:')
            if len(parts) == 2:
                fixed_lines.append(parts[0].rstrip() + '\n')
                fixed_lines.append('    registered_capital:' + parts[1])
                print(f"修复 Line {i+1}: 分割为两行")
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"\nOK - 所有语法错误已修复")

if __name__ == '__main__':
    main()
