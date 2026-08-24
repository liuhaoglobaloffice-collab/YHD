import re
from pathlib import Path

def fix_require_permission(file_path):
    content = Path(file_path).read_text(encoding='utf-8')
    # Replace 'resource:action' with 'resource', 'action'
    pattern = r'require_permission\("([^:]+):([^"]+)"\)'
    replacement = r'require_permission("\1", "\2")'
    new_content = re.sub(pattern, replacement, content)
    if new_content != content:
        Path(file_path).write_text(new_content, encoding='utf-8', newline='\n')
        print(f'Fixed: {file_path}')
        return True
    return False

files = [
    'src/api/routes/users.py',
    'src/api/routes/approvals.py',
    'src/api/routes/audit.py',
    'src/api/routes/roles.py',
]

fixed_count = 0
for f in files:
    try:
        if Path(f).exists():
            if fix_require_permission(f):
                fixed_count += 1
    except Exception as e:
        print(f'Error in {f}: {e}')

print(f'\nTotal files fixed: {fixed_count}')
