#!/usr/bin/env python3
"""Deep debug: Track where routes disappear"""

import sys
import os
from pathlib import Path

# Set env before imports
os.environ['SECRET_KEY'] = 'H0OOgF7Hu8G40TtZnN_QCyAPGInurI9X6K39GUXTTBQ'
os.environ['JWT_SECRET_KEY'] = 'FD567ckE0cOXIiwBhkt3YNInrIn62jPHneF-JAIWBwI'

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("PHASE 1: Import api_router")
print("=" * 80)

from src.api.routes import api_router

print(f"api_router: {api_router}")
print(f"api_router.prefix: {api_router.prefix}")
print(f"api_router.routes count: {len(api_router.routes)}")

# Find supplier router
supplier_router_obj = None
for i, route in enumerate(api_router.routes):
    if hasattr(route, 'original_router'):
        router_id = id(route.original_router)
        # Check if this router has supplier endpoints
        if hasattr(route.original_router, 'routes'):
            for sub_route in route.original_router.routes:
                if hasattr(sub_route, 'path') and 'supplier' in sub_route.path:
                    supplier_router_obj = route.original_router
                    print(f"\n[FOUND] Supplier router at index {i}")
                    print(f"  Router ID: {router_id}")
                    print(f"  Routes: {len(route.original_router.routes)}")
                    break

print("\n" + "=" * 80)
print("PHASE 2: Create FastAPI app manually")
print("=" * 80)

from fastapi import FastAPI

manual_app = FastAPI(
    title="Test App",
    version="1.0.0",
)

print(f"\nApp created: {manual_app}")
print(f"App routes before include_router: {len(manual_app.routes)}")

# Include api_router
manual_app.include_router(api_router)

print(f"App routes after include_router: {len(manual_app.routes)}")

# List all routes
print("\nAll routes in manual_app:")
for route in manual_app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', set())
        path = route.path
        print(f"  {','.join(sorted(methods - {'HEAD', 'OPTIONS'})):10} {path}")

# Check for supplier routes
supplier_found = [r for r in manual_app.routes if hasattr(r, 'path') and 'supplier' in r.path.lower()]
print(f"\nSupplier routes found: {len(supplier_found)}")

print("\n" + "=" * 80)
print("PHASE 3: Check api_router internal structure")
print("=" * 80)

# Access FastAPI's internal route resolution
from fastapi.routing import APIRoute

def flatten_routes(router, prefix=""):
    """Recursively flatten all routes"""
    routes = []
    for route in router.routes:
        if hasattr(route, 'path') and isinstance(route, APIRoute):
            full_path = prefix + route.path
            routes.append((route.methods, full_path, route))
        elif hasattr(route, 'original_router'):
            # This is an IncludedRouter
            sub_prefix = prefix + getattr(route.include_context, 'prefix', '')
            routes.extend(flatten_routes(route.original_router, sub_prefix))
    return routes

print("\nFlattening api_router routes...")
flat_routes = flatten_routes(api_router, api_router.prefix)
print(f"Total flattened routes: {len(flat_routes)}")

supplier_flat = [r for r in flat_routes if 'supplier' in r[1].lower()]
print(f"Supplier routes in flattened list: {len(supplier_flat)}")

if supplier_flat:
    print("\nSupplier routes:")
    for methods, path, route in supplier_flat:
        print(f"  {','.join(sorted(methods - {'HEAD', 'OPTIONS'})):10} {path}")

print("\n" + "=" * 80)
print("PHASE 4: Use create_app() from src.api.app")
print("=" * 80)

from src.api.app import create_app

real_app = create_app()
print(f"\nReal app created: {real_app}")
print(f"Real app routes: {len(real_app.routes)}")

print("\nAll routes in real_app:")
for route in real_app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', set())
        path = route.path
        print(f"  {','.join(sorted(methods - {'HEAD', 'OPTIONS'})):10} {path}")

# Check for supplier
supplier_in_real = [r for r in real_app.routes if hasattr(r, 'path') and 'supplier' in r.path.lower()]
print(f"\nSupplier routes in real_app: {len(supplier_in_real)}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if supplier_flat and not supplier_in_real:
    print("\n[ERROR] Routes exist in api_router but disappear in app!")
    print("Possible causes:")
    print("  - Lifespan manager interference")
    print("  - Middleware issue")
    print("  - Import order problem")
    print("  - FastAPI version bug")
elif supplier_flat and supplier_in_real:
    print("\n[SUCCESS] Routes properly registered!")
else:
    print("\n[ERROR] Routes never existed in api_router!")
