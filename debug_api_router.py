#!/usr/bin/env python3
"""Debug API Router Registration"""

import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("[STEP 1] Importing api_router...")
try:
    from src.api.routes import api_router
    print(f"  [OK] api_router imported: {api_router}")
    print(f"  [OK] api_router type: {type(api_router)}")
    print(f"  [OK] api_router prefix: {api_router.prefix}")
    
    # Check routes inside api_router
    if hasattr(api_router, 'routes'):
        print(f"  [OK] api_router.routes count: {len(api_router.routes)}")
        for route in api_router.routes:
            if hasattr(route, 'path'):
                methods = getattr(route, 'methods', set())
                print(f"    - {','.join(methods):10} {route.path}")
    else:
        print("  [WARN] api_router has no 'routes' attribute")
        
except Exception as e:
    print(f"  [ERROR] Failed to import api_router: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[STEP 2] Importing supplier router...")
try:
    from src.api.routes import supplier
    print(f"  [OK] supplier module imported: {supplier}")
    print(f"  [OK] supplier.router: {supplier.router}")
    print(f"  [OK] supplier.router prefix: {supplier.router.prefix}")
    
    if hasattr(supplier.router, 'routes'):
        print(f"  [OK] supplier.router.routes count: {len(supplier.router.routes)}")
        for route in supplier.router.routes:
            if hasattr(route, 'path'):
                methods = getattr(route, 'methods', set())
                print(f"    - {','.join(methods):10} {route.path}")
    
except Exception as e:
    print(f"  [ERROR] Failed to import supplier: {e}")
    import traceback
    traceback.print_exc()

print("\n[STEP 3] Checking if supplier.router is in api_router...")
try:
    from src.api.routes import api_router, supplier
    
    # Check if supplier router was included
    found = False
    for route in api_router.routes:
        route_str = str(route)
        if 'supplier' in route_str.lower():
            found = True
            print(f"  [OK] Found supplier route: {route}")
    
    if not found:
        print("  [ERROR] supplier.router was NOT included in api_router!")
        print("\n  [DEBUG] api_router.routes:")
        for i, route in enumerate(api_router.routes):
            print(f"    {i}: {route}")
            
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n[STEP 4] Creating app and checking final routes...")
try:
    import os
    os.environ['SECRET_KEY'] = 'H0OOgF7Hu8G40TtZnN_QCyAPGInurI9X6K39GUXTTBQ'
    os.environ['JWT_SECRET_KEY'] = 'FD567ckE0cOXIiwBhkt3YNInrIn62jPHneF-JAIWBwI'
    
    from src.api.app import create_app
    
    app = create_app()
    print(f"  [OK] App created: {app}")
    print(f"  [OK] App routes count: {len(app.routes)}")
    
    supplier_found = False
    for route in app.routes:
        if hasattr(route, 'path'):
            if 'supplier' in route.path.lower():
                supplier_found = True
                methods = getattr(route, 'methods', set())
                print(f"    [OK] {','.join(methods):10} {route.path}")
    
    if not supplier_found:
        print("  [ERROR] No supplier routes in final app!")
        print("\n  [DEBUG] All app routes:")
        for route in app.routes:
            if hasattr(route, 'path'):
                methods = getattr(route, 'methods', set())
                print(f"    - {','.join(methods):10} {route.path}")
        
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n[DONE]")
