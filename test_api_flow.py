import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing Full Supplier API Flow...")
print("=" * 60)

# Step 1: Register and Login
print("\n1. Login...")
try:
    # Register if needed
    register_data = {
        "username": "apitest",
        "password": "testpass123",
        "email": "apitest@example.com",
        "full_name": "API Test User"
    }
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_data)
    if r.status_code in [200, 201]:
        print("   User registered")
    
    # Login
    login_data = {
        "username": "apitest",
        "password": "testpass123"
    }
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    print(f"   Login status: {r.status_code}")
    
    if r.status_code == 200:
        token_data = r.json()
        access_token = token_data.get('access_token')
        print(f"   Got token: {access_token[:30]}...")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Get suppliers list
        print("\n2. GET /api/v1/suppliers")
        r2 = requests.get(f"{BASE_URL}/api/v1/suppliers", headers=headers)
        print(f"   Status: {r2.status_code}")
        
        if r2.status_code == 200:
            suppliers = r2.json()
            print(f"   Got {len(suppliers)} suppliers")
            if suppliers:
                for s in suppliers[:3]:
                    print(f"     - {s.get('name', 'N/A')}")
        else:
            print(f"   Response: {r2.text[:200]}")
            
        # Step 3: Create a test supplier
        print("\n3. POST /api/v1/suppliers (create)")
        supplier_data = {
            "name": "Test Supplier Co",
            "business_type": "manufacturer",
            "status": "active",
            "contact_name": "Zhang San",
            "contact_email": "zhangsan@test.com",
            "contact_phone": "13800138000",
            "address": "Shenzhen Nanshan"
        }
        r3 = requests.post(f"{BASE_URL}/api/v1/suppliers", headers=headers, json=supplier_data)
        print(f"   Status: {r3.status_code}")
        
        if r3.status_code == 201:
            created_supplier = r3.json()
            supplier_id = created_supplier.get('id')
            print(f"   Created supplier ID: {supplier_id}")
            
            # Step 4: Get single supplier
            print("\n4. GET /api/v1/suppliers/{supplier_id}")
            r4 = requests.get(f"{BASE_URL}/api/v1/suppliers/{supplier_id}", headers=headers)
            print(f"   Status: {r4.status_code}")
            if r4.status_code == 200:
                supplier = r4.json()
                print(f"   Name: {supplier.get('name')}")
                print(f"   Type: {supplier.get('business_type')}")
                print(f"   Status: {supplier.get('status')}")
        elif r3.status_code == 403:
            print(f"   Permission denied: {r3.text[:150]}")
        else:
            print(f"   Response: {r3.text[:200]}")
            
    else:
        print(f"   Login failed: {r.text}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test completed!")
