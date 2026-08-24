import sqlite3

conn = sqlite3.connect(r'D:\LiuHao-AI-OS\liuhao_ai_os_production.db')
cursor = conn.cursor()

cursor.execute('SELECT id, username, hashed_password, role, is_active FROM users')
users = cursor.fetchall()

print("Current users in production database:")
for user in users:
    print(f"ID: {user[0]}")
    print(f"Username: {user[1]}")
    print(f"Password Hash: {user[2][:50]}...")
    print(f"Role: {user[3]}")
    print(f"Active: {user[4]}")
    print()

conn.close()
