"""Fix test_governance.py duplicate parameters"""

with open('tests/test_identity/test_governance.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
for i, line in enumerate(lines):
    # Check for duplicate admin_user parameters
    if ', admin_user: User, admin_user: User' in line:
        # Replace second admin_user with target_user
        line = line.replace(', admin_user: User, admin_user: User', ', admin_user: User, target_user: User')
    elif ', admin_user: User, admin_user\)' in line:
        line = line.replace(', admin_user: User, admin_user)', ', admin_user: User, target_user: User)')
    
    fixed_lines.append(line)

with open('tests/test_identity/test_governance.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print('Fixed duplicate parameters')
