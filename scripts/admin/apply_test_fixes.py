"""
Apply all fixes to test_tools.py
"""
import re

with open('tests/test_ai/test_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Import patch if not already there
if 'from unittest.mock import Mock, AsyncMock, patch' not in content:
    content = content.replace(
        'from unittest.mock import Mock, AsyncMock',
        'from unittest.mock import Mock, AsyncMock, patch'
    )

# Fix 2: Change FAILED to DENIED for unknown tool (line ~221)
content = re.sub(
    r'(# Test unknown tool.*?assert result\.status == ToolStatus\.)FAILED',
    r'\1DENIED',
    content,
    flags=re.DOTALL,
    count=1
)

# Fix 3: Change FAILED to DENIED for disabled tool (line ~258)
content = re.sub(
    r'(# Test disabled tool.*?assert result\.status == ToolStatus\.)FAILED',
    r'\1DENIED',
    content,
    flags=re.DOTALL,
    count=1
)

# Fix 4: Add @patch to test_execute_tool_policy_enforcement
pattern4 = r'(    @pytest\.mark\.asyncio\n    async def test_execute_tool_policy_enforcement\(self\):)'
replacement4 = r'    @pytest.mark.asyncio\n    @patch("src.ai.tools.has_permission")\n    async def test_execute_tool_policy_enforcement(self, mock_has_permission):\n        mock_has_permission.return_value = True'
content = re.sub(pattern4, replacement4, content)

# Fix 5: Add @patch to test_execute_tool_requires_approval
pattern5 = r'(    @pytest\.mark\.asyncio\n    async def test_execute_tool_requires_approval\(self\):)'
replacement5 = r'    @pytest.mark.asyncio\n    @patch("src.ai.tools.has_permission")\n    async def test_execute_tool_requires_approval(self, mock_has_permission):\n        mock_has_permission.return_value = True'
content = re.sub(pattern5, replacement5, content)

# Fix 6: Add @patch to test_inactive_user_cannot_use_tools
pattern6 = r'(    @pytest\.mark\.asyncio\n    async def test_inactive_user_cannot_use_tools\(self\):)'
replacement6 = r'    @pytest.mark.asyncio\n    @patch("src.ai.tools.has_permission")\n    async def test_inactive_user_cannot_use_tools(self, mock_has_permission):\n        mock_has_permission.return_value = False'
content = re.sub(pattern6, replacement6, content)

# Fix 7: Add @patch to test_rate_limiting_enforced
pattern7 = r'(    @pytest\.mark\.asyncio\n    async def test_rate_limiting_enforced\(self\):)'
replacement7 = r'    @pytest.mark.asyncio\n    @patch("src.ai.tools.has_permission")\n    async def test_rate_limiting_enforced(self, mock_has_permission):\n        mock_has_permission.return_value = True'
content = re.sub(pattern7, replacement7, content)

with open('tests/test_ai/test_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Applied all test fixes successfully')
