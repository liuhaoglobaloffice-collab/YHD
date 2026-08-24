#!/usr/bin/env python3
"""从头重建 supplier.py，确保 batch 路由在 /{supplier_id} 之前"""

import subprocess
import sys

# 首先，让我们检查文件是否损坏
with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# 查找问题行
for i, line in enumerate(lines[260:280], start=260):
    if 'assessment_date' in line and line.strip().startswith('assessment_date'):
        print(f"Line {i+1}: ORPHAN - {line.strip()[:80]}")

# 由于文件已损坏，我们需要从最近的工作脚本恢复
# 让我们检查是否还有其他备份或者重新应用所有修复

print("\nFile appears corrupted. Need manual intervention.")
print("Please restore from backup or re-apply all P1-P3 fixes.")
sys.exit(1)
