import importlib, os, sqlite3, asyncio
import src.database.base as base

print('database_url:', base.get_database_url())
print('metadata tables before import:', sorted(base.Base.metadata.tables.keys()))
import src.database.provider_metrics_model
print('metadata tables after import:', sorted(base.Base.metadata.tables.keys()))
asyncio.get_event_loop().run_until_complete(base.init_database())
print('init_database called')
# check sqlite file existence
db_path = 'liuhaos_ai_os.db'
print('db file exists', os.path.exists(db_path))
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('sqlite tables:', cur.fetchall())
    conn.close()
