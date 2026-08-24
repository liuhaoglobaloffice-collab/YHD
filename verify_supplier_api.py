import os
os.environ['SECRET_KEY'] = 'H0OOgF7Hu8G40TtZnN_QCyAPGInurI9X6K39GUXTTBQ'
os.environ['JWT_SECRET_KEY'] = 'FD567ckE0cOXIiwBhkt3YNInrIn62jPHneF-JAIWBwI'

from src.api.app import create_app

app = create_app()
schema = app.openapi()

supplier_paths = [(p, list(schema['paths'][p].keys())) for p in schema['paths'].keys() if 'supplier' in p.lower()]

print(f"\n[OK] Supplier API Endpoints: {len(supplier_paths)}\n")
for path, methods in sorted(supplier_paths):
    print(f"  {', '.join(methods):20} {path}")

print(f"\n[INFO] Total API paths: {len(schema['paths'])}")
