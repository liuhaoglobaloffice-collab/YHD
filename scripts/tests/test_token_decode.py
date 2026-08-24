import jwt
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载生产环境配置
load_dotenv(Path(r'D:\LiuHao-AI-OS\.env.production'))

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzg3NTUxMTI2fQ.gGJZADWGmaA4xLAdvaPv_RFmP2xv3v-W_XoA0ghz7jo'
secret = os.getenv('JWT_SECRET_KEY')

print(f'Secret Key: {secret}')
print(f'Token: {token[:50]}...')

try:
    decoded = jwt.decode(token, secret, algorithms=['HS256'])
    print(f'\nDecoded Token:')
    print(f'  sub (user_id): {decoded["sub"]}')
    print(f'  role: {decoded["role"]}')
    print(f'  exp: {decoded["exp"]}')
except Exception as e:
    print(f'\nError: {e}')
