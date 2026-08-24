"""验证Dashboard数据"""

from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///./data/liuhao_ai_os.db')
conn = engine.connect()

print('=== Dashboard数据统计 ===')
print(f'供应商总数: {conn.execute(text("SELECT COUNT(*) FROM suppliers")).scalar()}')
print(f'活跃供应商: {conn.execute(text("SELECT COUNT(*) FROM suppliers WHERE status=\'ACTIVE\'")).scalar()}')
print(f'联系人数: {conn.execute(text("SELECT COUNT(*) FROM supplier_contacts")).scalar()}')
print(f'证书数: {conn.execute(text("SELECT COUNT(*) FROM supplier_certificates")).scalar()}')
print(f'风险评估数: {conn.execute(text("SELECT COUNT(*) FROM supplier_risk_assessments")).scalar()}')
print('')
print('=== 风险等级分布 ===')
result = conn.execute(text('SELECT risk_level, COUNT(*) FROM supplier_risk_assessments GROUP BY risk_level'))
for r in result:
    print(f'{r[0]}: {r[1]}')

print('')
print('=== 供应商状态分布 ===')
result = conn.execute(text('SELECT status, COUNT(*) FROM suppliers GROUP BY status'))
for r in result:
    print(f'{r[0]}: {r[1]}')

conn.close()
