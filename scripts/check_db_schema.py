import sqlite3

conn = sqlite3.connect('./data/liuhao_ai_os.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('数据库表:')
for table in tables:
    print(f'  - {table[0]}')

# 查看 users 表结构
print('\nusers 表结构:')
cursor.execute('PRAGMA table_info(users)')
columns = cursor.fetchall()
for col in columns:
    print(f'  {col[1]} ({col[2]})')

conn.close()
