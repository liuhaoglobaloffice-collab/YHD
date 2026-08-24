#!/usr/bin/env python3
"""
Test decode logic
"""
from src.identity.auth import decode_access_token

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzg3NTQ5NTczfQ.PwfxF72mqHZR9N5IUw4gYVJd30C9wJx94slY8HZvd1E"

payload = decode_access_token(token)
print(f"Payload: {payload}")
print(f"sub: {payload.get('sub')} (type: {type(payload.get('sub'))})")

user_id_str = payload.get("sub")
user_id = int(user_id_str) if user_id_str else None
print(f"user_id after conversion: {user_id} (type: {type(user_id)})")
