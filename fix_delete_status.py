with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('status_code=204', 'status_code=200')

with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed')
