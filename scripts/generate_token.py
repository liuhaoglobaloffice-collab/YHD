"""生成测试JWT Token"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from src.identity.auth import create_access_token

if __name__ == "__main__":
    token = create_access_token({"sub": "test_user", "role": "admin"})
    print(token)
