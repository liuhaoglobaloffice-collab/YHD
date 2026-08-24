#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量修复 App.tsx 中的 PlaceholderPage 调用"""

import re

# 读取文件
with open(r"D:\LiuHao-AI-OS\frontend\src\App.tsx", 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有 <PlaceholderPage module="..." page="..." /> 为 <PlaceholderPage title="..." />
# 优先使用 page 作为 title
content = re.sub(
    r'<PlaceholderPage module="[^"]*" page="([^"]*)" />',
    r'<PlaceholderPage title="\1" />',
    content
)

# 写回文件
with open(r"D:\LiuHao-AI-OS\frontend\src\App.tsx", 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all PlaceholderPage calls")
