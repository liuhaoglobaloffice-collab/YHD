import re

with open('tests/integration/test_supplier_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all long code formats with short format SUP + 4-8 digits
replacements = [
    (r'"code": f"SUP\{timestamp\[:12\]\}"', '"code": f"SUP{int(timestamp[12:]) % 99999}"'),
    (r'"code": f"SUP6002-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:]) % 88888}"'),
    (r'"code": f"SUP6003-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:]) % 77777}"'),
    (r'"code": f"SUP6004-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:]) % 66666}"'),
    (r'"code": f"SUP610\{i\}-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:18]) % 9999}{i}"'),
    (r'"code": f"SUP6201-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:]) % 55555}"'),
    (r'"code": f"SUP640\{i\}\{timestamp\[:8\]\}"', '"code": f"SUP{int(timestamp[12:17]) % 8888}{i}"'),
    (r'"code": f"SUP650\{i\}\{timestamp\[:8\]\}"', '"code": f"SUP{int(timestamp[12:17]) % 7777}{i}"'),
    (r'"code": f"SUP700\{i\}-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:18]) % 8888}{i}"'),
    (r'"code": f"SUP8001-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:]) % 44444}"'),
    (r'"code": f"SUP8002-\{timestamp\}"', '"code": f"SUP{int(timestamp[12:]) % 33333}"'),
    (r'assert data\["code"\] == f"SUP\{timestamp\[:12\]\}"', 'assert data["code"] == f"SUP{int(timestamp[12:]) % 99999}"'),
    (r'assert data\["code"\] == f"SUP6002-\{timestamp\}"', 'assert data["code"] == f"SUP{int(timestamp[12:]) % 88888}"'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open('tests/integration/test_supplier_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Code format fixes applied')
