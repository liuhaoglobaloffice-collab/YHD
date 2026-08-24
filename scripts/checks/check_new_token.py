import jwt

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzg3NDY1Mzc1fQ.FDpxW80jTXN6bytbHQ3ikQuwdzJA7UGa2xPj00KIfxA'

decoded = jwt.decode(token, options={'verify_signature': False})

print(f"Token Payload:")
print(f"  sub: {decoded.get('sub')} (type: {type(decoded.get('sub'))})")
print(f"  role: {decoded.get('role')}")
print(f"  exp: {decoded.get('exp')}")
