"""Fix test_identity/test_governance.py fixture names"""

with open('tests/test_identity/test_governance.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix db_session -> async_session
content = content.replace('db_session: AsyncSession', 'async_session: AsyncSession')
content = content.replace('(db_session,', '(async_session,')
content = content.replace('(db_session)', '(async_session)')

# Fix test_user -> admin_user more carefully
# Only replace in function signatures and where it's clearly the fixture
import re

# Fix function parameters
content = re.sub(
    r'(\btest_user: User)',
    r'admin_user: User',
    content
)

# Fix references in function bodies
content = re.sub(
    r'\btest_user\.',
    r'admin_user.',
    content
)
content = re.sub(
    r'\(test_user\)',
    r'(admin_user)',
    content
)
content = re.sub(
    r', test_user\)',
    r', admin_user)',
    content
)

with open('tests/test_identity/test_governance.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed governance test fixtures')
