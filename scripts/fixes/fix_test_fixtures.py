"""
Fix test_knowledge_retrieval.py fixtures to use Model instances
"""
import re

# Read file
with open('tests/test_knowledge/test_knowledge_retrieval.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Process line by line
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Add imports after CompanyBrainEntityRepository import
    if 'from src.database.repositories.knowledge import (' in line:
        new_lines.append(line)
        new_lines.append(lines[i+1])  # MemoryRepository,
        new_lines.append(lines[i+2])  # CompanyBrainEntityRepository,
        new_lines.append(lines[i+3])  # )
        new_lines.append('from src.database.models import MemoryModel, CompanyBrainEntityModel\n')
        new_lines.append('from uuid import uuid4\n')
        i += 4
        continue
    
    # Fix memory_repo.create calls
    if 'await memory_repo.create(' in line and 'MemoryModel' not in line:
        # This is the old style, replace with MemoryModel()
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + 'await memory_repo.create(MemoryModel(\n')
        new_lines.append(' ' * (indent + 4) + 'id=str(uuid4()),\n')
        i += 1
        # Copy parameters until closing paren
        while i < len(lines):
            param_line = lines[i]
            if ')),' in param_line or '        ),' in param_line:
                new_lines.append(param_line.replace('),', ')),'))
                i += 1
                break
            else:
                new_lines.append(param_line)
                i += 1
        continue
    
    # Fix entity_repo.create calls
    if 'await entity_repo.create(' in line and 'CompanyBrainEntityModel' not in line:
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + 'await entity_repo.create(CompanyBrainEntityModel(\n')
        new_lines.append(' ' * (indent + 4) + 'id=str(uuid4()),\n')
        i += 1
        while i < len(lines):
            param_line = lines[i]
            if ')),' in param_line or '        ),' in param_line:
                new_lines.append(param_line.replace('),', ')),'))
                i += 1
                break
            else:
                new_lines.append(param_line)
                i += 1
        continue
    
    new_lines.append(line)
    i += 1

# Write back
with open('tests/test_knowledge/test_knowledge_retrieval.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('OK Fixed test fixtures')
