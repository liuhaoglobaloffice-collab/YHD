"""Verify sub-account registration and listing."""
import urllib.request, json

# Register main account
d = json.dumps({'username': 'liuhao', 'email': 'liuhaoglobal.office@gmail.com', 'password': 'yhd06110720jyc', 'full_name': 'Admin', 'role': 'user'}).encode()
r = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/v1/auth/register', data=d, headers={'Content-Type': 'application/json'}))
print('Register main:', r.status)

# Register sub account
d2 = json.dumps({'username': 'yhd257900', 'password': 'yhd06110720jyc'}).encode()
r2 = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/v1/auth/register-sub', data=d2, headers={'Content-Type': 'application/json'}))
result2 = json.loads(r2.read().decode())
print('Sub register:', r2.status, result2['message'])

# Login
d3 = json.dumps({'username': 'liuhao', 'password': 'yhd06110720jyc'}).encode()
r3 = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=d3, headers={'Content-Type': 'application/json'}))
token = json.loads(r3.read().decode())['access_token']

# List sub-accounts
r4 = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/v1/accounts/sub-accounts', headers={'Authorization': 'Bearer ' + token}))
result = json.loads(r4.read().decode())
print('Sub-accounts total:', result['total'])
for x in result['sub_accounts']:
    print('  -', x['username'], 'active=', x['is_active'], 'status=', x.get('approval_status', 'N/A'))

# Pending approvals
r5 = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/v1/accounts/pending-approvals', headers={'Authorization': 'Bearer ' + token}))
result5 = json.loads(r5.read().decode())
print('Pending approvals:', result5['total'])
for x in result5['sub_accounts']:
    print('  -', x['username'], 'status=', x.get('approval_status', 'N/A'))

print('All OK!')