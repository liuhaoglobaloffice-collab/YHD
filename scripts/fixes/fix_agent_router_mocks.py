"""Fix test_agent_router.py - use proper AIEmployee mock objects"""
import re

# Read the file
with open("tests/test_ai_brain/test_agent_router.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Add necessary imports at the top
import_idx = None
for i, line in enumerate(lines):
    if line.startswith("from src.ai.agent_router"):
        import_idx = i + 1
        break

if import_idx:
    lines.insert(import_idx, "from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position\n")
    lines.insert(import_idx + 1, "from uuid import uuid4\n")

# Fix mock employee objects - replace dict with Mock objects
new_lines = []
in_list_employees = False
skip_next = False

for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue
        
    # Look for list_employees return_value with dict
    if "router.registry.list_employees = AsyncMock(return_value=[" in line:
        # Get the dict content
        dict_start = i
        dict_content = line
        
        # Find the closing bracket
        if "]))" not in line:
            j = i + 1
            while j < len(lines) and "]))" not in lines[j]:
                dict_content += lines[j]
                j += 1
            if j < len(lines):
                dict_content += lines[j]
        
        # Replace with Mock object creation
        indent = " " * (len(line) - len(line.lstrip()))
        
        # Extract agent_type from dict if present
        agent_type = "business"
        if '"agent_type": "research"' in dict_content:
            agent_type = "research"
        elif '"agent_type": "sales"' in dict_content:
            agent_type = "sales"
        elif '"agent_type": "marketing"' in dict_content:
            agent_type = "marketing"
        
        # Create proper mock
        new_lines.append(f"{indent}mock_employee = Mock(spec=AIEmployee)\n")
        new_lines.append(f"{indent}mock_employee.id = uuid4()\n")
        new_lines.append(f"{indent}mock_employee.name = '{agent_type.title()} Agent'\n")
        new_lines.append(f"{indent}mock_employee.status = AIEmployeeStatus.ACTIVE\n")
        new_lines.append(f"{indent}router.registry.list_employees = AsyncMock(return_value=[mock_employee])\n")
        
        # Skip the original lines
        if "]))" in line:
            skip_next = False
        else:
            # Skip until we find the closing
            while i < len(lines) - 1 and "]))" not in lines[i]:
                i += 1
                skip_next = True
        continue
    
    new_lines.append(line)

# Write back
with open("tests/test_ai_brain/test_agent_router.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Fixed test_agent_router.py - replaced dict with AIEmployee mock objects")
