# -*- coding: utf-8 -*-
import requests
import jwt
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"
JWT_SECRET = "FD567ckE0cOXIiwBhkt3YNInrIn62jPHneF-JAIWBwI"
JWT_ALGORITHM = "HS256"

def generate_token():
    payload = {
        "sub": "1",  # user_id from database
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def test_contact_crud():
    token = generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Use existing supplier ID from database
    supplier_id = "7"  # LG Electronics Inc.
    
    print("=== Test Supplier Contact CRUD ===\n")
    
    # 1. Create Contact
    print("[1/4] Creating contact...")
    contact_data = {
        "name": "Zhang San",
        "job_title": "Sales Manager",
        "phone": "13800138000",
        "email": "zhangsan@example.com",
        "wechat": "zhangsan_wx",
        "qq": "123456789",
        "is_primary": True,
        "remarks": "Main contact person"
    }
    
    response = requests.post(
        f"{BASE_URL}/suppliers/{supplier_id}/contacts",
        json=contact_data,
        headers=headers
    )
    
    if response.status_code == 200:
        contact = response.json()
        contact_id = contact["id"]
        print(f"OK - Contact created: ID={contact_id}, Name={contact['name']}")
    else:
        print(f"FAIL - {response.status_code}: {response.text}")
        return
    
    # 2. Get Contacts
    print("\n[2/4] Getting contacts...")
    response = requests.get(f"{BASE_URL}/suppliers/{supplier_id}/contacts", headers=headers)
    
    if response.status_code == 200:
        contacts = response.json()
        print(f"OK - Found {len(contacts)} contacts")
        for c in contacts:
            print(f"  - {c['name']} ({c['job_title']})")
    else:
        print(f"FAIL - {response.status_code}: {response.text}")
    
    # 3. Update Contact
    print("\n[3/4] Updating contact...")
    update_data = {
        "job_title": "Senior Sales Manager",
        "phone": "13900139000"
    }
    
    response = requests.put(
        f"{BASE_URL}/suppliers/{supplier_id}/contacts/{contact_id}",
        json=update_data,
        headers=headers
    )
    
    if response.status_code == 200:
        updated = response.json()
        print(f"OK - Contact updated: {updated['job_title']}, {updated['phone']}")
    else:
        print(f"FAIL - {response.status_code}: {response.text}")
    
    # 4. Delete Contact
    print("\n[4/4] Deleting contact...")
    response = requests.delete(
        f"{BASE_URL}/suppliers/{supplier_id}/contacts/{contact_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"OK - {result['message']}")
    else:
        print(f"FAIL - {response.status_code}: {response.text}")
    
    # Verify deletion
    print("\n[Verify] Checking deletion...")
    response = requests.get(f"{BASE_URL}/suppliers/{supplier_id}/contacts", headers=headers)
    if response.status_code == 200:
        contacts = response.json()
        print(f"OK - Contacts remaining: {len(contacts)}")
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    test_contact_crud()
