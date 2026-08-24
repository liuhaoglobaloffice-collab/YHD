with open('src/workflow/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the missing if statement - need to find all occurrences
import re

# Pattern: model = await ... followed by raise without if
pattern = r'(model = await self\.repo\.get_by_id\(str\(workflow_id\)\))\n(        )(raise ValueError)'
replacement = r'\1\n\2if not model:\n\2    \3'

content = re.sub(pattern, replacement, content)

with open('src/workflow/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed workflow service')
