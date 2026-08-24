import requests
import jwt
from datetime import datetime, timedelta, timezone

# 测试JWT和权限系统
JWT_SECRET = 'FD567ckE0cOXIiwBhkt3YNInrIn62jPHneF-JAIWBwI'
BASE_URL = 'http://localhost:8000/api/v1'

# 1. 测试无需权限的端点（获取供应商列表）
print("=== Test 1: Get suppliers (no auth) ===")
response = requests.get(f"{BASE_URL}/suppliers")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    suppliers = response.json()
    print(f"Found {len(suppliers)} suppliers")
    if suppliers:
        print(f"First supplier ID: {suppliers[0]['id']}")
else:
    print(f"Error: {response.text}")

print()

# 2. 测试JWT token生成和验证
print("=== Test 2: JWT Token ===")
payload = {
    'sub': '1',  # user_id
    'role': 'admin',
    'exp': datetime.now(timezone.utc) + timedelta(hours=1)  # UTC时间
}
token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
print(f"Generated token: {token[:50]}...")

# 验证token
try:
    decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    print(f"Token valid: user_id={decoded['sub']}, role={decoded['role']}")
except Exception as e:
    print(f"Token invalid: {e}")

print()

# 3. 测试需要认证的端点（获取单个供应商）
print("=== Test 3: Get supplier by ID (with auth) ===")
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(f"{BASE_URL}/suppliers/7", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    supplier = response.json()
    print(f"Supplier: {supplier['name']}")
elif response.status_code == 401:
    print(f"Auth failed: {response.text}")
else:
    print(f"Error: {response.text}")

print()

# 4. 测试创建联系人（需要权限）
print("=== Test 4: Create contact (with permission) ===")
contact_data = {
    'name': 'Zhang San',
    'job_title': 'Sales Manager',
    'phone': '13800138000',
    'email': 'zhangsan@example.com',
    'wechat': 'zhangsan_wx',
    'qq': '123456789',
    'is_primary': True,
    'remarks': 'Main contact'
}
response = requests.post(
    f"{BASE_URL}/suppliers/7/contacts",
    json=contact_data,
    headers=headers
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    contact = response.json()
    print(f"Contact created: ID={contact.get('id')}, Name={contact.get('name')}")
elif response.status_code == 401:
    print(f"Auth failed: {response.text}")
elif response.status_code == 403:
    print(f"Permission denied: {response.text}")
else:
    print(f"Error: {response.text}")
