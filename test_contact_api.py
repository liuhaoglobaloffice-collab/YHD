#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试供应商联系人API - 使用直接生成的token"""
import requests
import json
import sys
import io
from datetime import datetime, timedelta

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000/api/v1"

# 1. 直接生成admin token（使用后端相同的JWT配置）
print("=" * 60)
print("步骤1: 生成测试Token")
print("=" * 60)

try:
    # 导入后端的JWT工具
    sys.path.insert(0, 'src')
    from core.security.jwt_handler import create_access_token
    
    # 创建admin token
    token_data = {
        "sub": "admin",
        "user_id": "admin",
        "username": "admin",
        "roles": ["admin"]
    }
    TOKEN = create_access_token(token_data, expires_delta=timedelta(hours=24))
    print(f"[OK] Token生成成功")
except Exception as e:
    print(f"[FAIL] Token生成失败: {e}")
    print("尝试使用备用方法...")
    
    # 备用方法：直接构造JWT
    import jwt
    from datetime import datetime, timedelta
    
    SECRET_KEY = "your-secret-key-change-in-production"  # 从config读取
    ALGORITHM = "HS256"
    
    payload = {
        "sub": "admin",
        "user_id": "admin", 
        "username": "admin",
        "roles": ["admin"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    TOKEN = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    print(f"[OK] 备用Token生成成功")

headers = {"Authorization": f"Bearer {TOKEN}"}

# 2. 获取第一个供应商ID
print("\n步骤2: 获取供应商列表")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/suppliers?page=1&page_size=5", headers=headers)
    if response.status_code == 200:
        suppliers = response.json().get("data", [])
        if suppliers:
            supplier_id = suppliers[0]["id"]
            print(f"[OK] 找到供应商: ID={supplier_id}, Name={suppliers[0].get('name', 'N/A')}")
        else:
            print("[FAIL] 没有找到供应商，需要先创建")
            exit(1)
    else:
        print(f"[FAIL] 获取供应商失败: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"[FAIL] 请求失败: {e}")
    exit(1)

# 3. 测试创建联系人
print("\n步骤3: 创建联系人")
print("=" * 60)
contact_data = {
    "name": "张三",
    "job_title": "销售经理",
    "phone": "13800138000",
    "email": "zhangsan@supplier.com",
    "wechat": "zhangsan_wx",
    "is_primary": True,
    "remarks": "主要对接人"
}

try:
    response = requests.post(
        f"{BASE_URL}/suppliers/{supplier_id}/contacts",
        headers=headers,
        json=contact_data
    )
    if response.status_code == 200:
        contact = response.json()
        contact_id = contact["id"]
        print(f"[OK] 创建成功: ID={contact_id}, Name={contact['name']}")
    else:
        print(f"[FAIL] 创建失败: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"[FAIL] 请求失败: {e}")
    exit(1)

# 4. 测试获取联系人列表
print("\n步骤4: 获取联系人列表")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/suppliers/{supplier_id}/contacts", headers=headers)
    if response.status_code == 200:
        contacts = response.json()
        print(f"[OK] 获取成功: 共 {len(contacts)} 个联系人")
        for c in contacts:
            print(f"   - {c['name']} ({c['job_title']}) - 主要: {c['is_primary']}")
    else:
        print(f"[FAIL] 获取失败: {response.status_code} - {response.text}")
except Exception as e:
    print(f"[FAIL] 请求失败: {e}")

# 5. 测试更新联系人
print("\n步骤5: 更新联系人")
print("=" * 60)
update_data = {
    "phone": "13900139000",
    "remarks": "已更新的备注"
}
try:
    response = requests.put(
        f"{BASE_URL}/suppliers/{supplier_id}/contacts/{contact_id}",
        headers=headers,
        json=update_data
    )
    if response.status_code == 200:
        updated = response.json()
        print(f"[OK] 更新成功: Phone={updated['phone']}, Remarks={updated['remarks']}")
    else:
        print(f"[FAIL] 更新失败: {response.status_code} - {response.text}")
except Exception as e:
    print(f"[FAIL] 请求失败: {e}")

# 6. 测试删除联系人
print("\n步骤6: 删除联系人")
print("=" * 60)
try:
    response = requests.delete(
        f"{BASE_URL}/suppliers/{supplier_id}/contacts/{contact_id}",
        headers=headers
    )
    if response.status_code == 200:
        result = response.json()
        print(f"[OK] 删除成功: {result.get('message', 'OK')}")
    else:
        print(f"[FAIL] 删除失败: {response.status_code} - {response.text}")
except Exception as e:
    print(f"[FAIL] 请求失败: {e}")

# 7. 验证删除
print("\n步骤7: 验证删除")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/suppliers/{supplier_id}/contacts", headers=headers)
    if response.status_code == 200:
        contacts = response.json()
        print(f"[OK] 验证成功: 剩余 {len(contacts)} 个联系人")
    else:
        print(f"[FAIL] 验证失败: {response.status_code}")
except Exception as e:
    print(f"[FAIL] 请求失败: {e}")

print("\n" + "=" * 60)
print("[OK] 联系人API测试完成")
print("=" * 60)
