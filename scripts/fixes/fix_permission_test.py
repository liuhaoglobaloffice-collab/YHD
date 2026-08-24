"""Fix permission test in test_knowledge_retrieval.py"""

with open('tests/test_knowledge/test_knowledge_retrieval.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Find the test function
    if 'async def test_search_without_permission_fails' in line:
        new_lines.append(line)  # function def
        new_lines.append(lines[i+1])  # docstring
        i += 2
        
        # Add mock import and setup
        new_lines.append('    from unittest.mock import AsyncMock\n')
        new_lines.append('    \n')
        new_lines.append('    # Mock RBAC to deny permission\n')
        new_lines.append('    retrieval_service.rbac.check_permission = AsyncMock(return_value=False)\n')
        new_lines.append('    \n')
        
        # Skip old comment line if exists
        while i < len(lines) and ('regular_user does not have' in lines[i] or lines[i].strip() == ''):
            i += 1
        
        continue
    
    new_lines.append(line)
    i += 1

with open('tests/test_knowledge/test_knowledge_retrieval.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed permission test')
