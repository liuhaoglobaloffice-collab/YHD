"""Fix test_agent_router.py - add task_id to all task dicts"""
import re
from uuid import uuid4

# Read the file
with open("tests/test_ai_brain/test_agent_router.py", "r", encoding="utf-8") as f:
    content = f.read()

# Pattern to match task = {...} that doesn't have task_id
pattern = r'(task = \{)("task": [^}]+)(\})'

def add_task_id(match):
    start = match.group(1)
    middle = match.group(2)
    end = match.group(3)
    
    # Check if task_id already exists
    if "task_id" in middle:
        return match.group(0)
    
    # Add task_id
    return f'{start}"task_id": "{uuid4()}", {middle}{end}'

# Replace all occurrences
content = re.sub(pattern, add_task_id, content)

# Also fix agent_type references (agent → agent_type)
content = content.replace('"agent": "research"', '"agent_type": "research"')
content = content.replace('"agent": "sales"', '"agent_type": "sales"')
content = content.replace('"agent": "marketing"', '"agent_type": "marketing"')
content = content.replace('"agent": "business"', '"agent_type": "business"')

# Write back
with open("tests/test_ai_brain/test_agent_router.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed test_agent_router.py - added task_id and fixed agent_type")
