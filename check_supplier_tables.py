#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查Supplier表是否已创建"""
import sqlite3
import sys

# 设置Windows控制台UTF-8输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

db_path = "data/liuhao_ai_os.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询所有supplier相关的表
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE '%supplier%'
        ORDER BY name
    """)
    
    tables = cursor.fetchall()
    
    print("=" * 60)
    print("[Supplier Tables Check]")
    print("=" * 60)
    
    if tables:
        print(f"\n[OK] Found {len(tables)} supplier tables:\n")
        for i, (table_name,) in enumerate(tables, 1):
            print(f"   {i}. {table_name}")
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"      L-- {len(columns)} columns")
    else:
        print("\n[ERROR] No supplier tables found!")
        print("\n[INFO] Possible reasons:")
        print("   1. Migration not applied yet")
        print("   2. Wrong database file")
        print("   3. Tables created with different prefix")
    
    # 检查迁移历史
    print("\n" + "=" * 60)
    print("[Migration History]")
    print("=" * 60)
    
    cursor.execute("""
        SELECT version_num FROM alembic_version
        ORDER BY version_num DESC LIMIT 5
    """)
    versions = cursor.fetchall()
    
    if versions:
        print(f"\n[OK] Current migration: {versions[0][0]}")
        if len(versions) > 1:
            print(f"\nRecent migrations:")
            for ver in versions:
                print(f"   - {ver[0]}")
    else:
        print("\n[WARN] No migration history found!")
    
    conn.close()
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    print(f"\n   Database: {db_path}")
