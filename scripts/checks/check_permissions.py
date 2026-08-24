import sqlite3

db_path = r'D:\LiuHao-AI-OS\liuhao_ai_os_production.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== DATABASE TABLES ===")
for table in tables:
    print(f"  - {table[0]}")

print("\n=== USER INFO ===")
cursor.execute("SELECT id, username, role, is_active FROM users")
users = cursor.fetchall()
for user in users:
    print(f"  User ID: {user[0]}, Username: {user[1]}, Role: {user[2]}, Active: {user[3]}")

# 检查是否有 roles 表
if 'roles' in [t[0] for t in tables]:
    print("\n=== ROLES ===")
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()
    for role in roles:
        print(f"  {role}")

# 检查是否有 permissions 表
if 'permissions' in [t[0] for t in tables]:
    print("\n=== PERMISSIONS ===")
    cursor.execute("SELECT * FROM permissions")
    permissions = cursor.fetchall()
    for perm in permissions:
        print(f"  {perm}")

# 检查是否有 role_permissions 表
if 'role_permissions' in [t[0] for t in tables]:
    print("\n=== ROLE PERMISSIONS ===")
    cursor.execute("SELECT * FROM role_permissions")
    role_perms = cursor.fetchall()
    for rp in role_perms:
        print(f"  {rp}")

conn.close()
