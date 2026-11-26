import os
import bcrypt
from itsdangerous import URLSafeTimedSerializer

# In production, use a real SECRET_KEY from .env
SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-sprint-key")
serializer = URLSafeTimedSerializer(SECRET_KEY)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# app/auth.py
def create_session(username: str, role: str) -> str:
    return serializer.dumps({"username": username, "role": role})

def get_user_from_session(session_token: str | None) -> dict | None:
    if not session_token: return None
    try:
        data = serializer.loads(session_token, max_age=86400)
        return {"username": data["username"], "role": data["role"]}
    except Exception:
        return None