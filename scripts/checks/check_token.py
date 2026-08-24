import jwt

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImV4cCI6MTc4NzQ2NTEyNX0.wVJQMJmuAVQOLy6t4BlVdUWIQlbI_CtPfjSuYxAqH8s'

# Decode without verification to see payload
decoded = jwt.decode(token, options={'verify_signature': False})

print(f"Token Payload:")
print(f"  sub: {decoded.get('sub')} (type: {type(decoded.get('sub'))})")
print(f"  exp: {decoded.get('exp')}")
print(f"  role: {decoded.get('role', 'N/A')}")
