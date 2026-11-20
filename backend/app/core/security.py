# backend/app/core/security.py
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from app.core.config import settings

def get_password_hash(password: str) -> str:
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if ":" not in hashed_password:
            return False
        salt, key_hex = hashed_password.split(":", 1)
        computed_key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(computed_key.hex(), key_hex)
    except Exception:
        return False

def create_access_token(subject: str, tenant_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def hash_token(token: str) -> str:
    """Hash collector API tokens for safe database storage"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def generate_collector_key() -> str:
    """Generate high-entropy collector secret key: ov_col_..."""
    return f"ov_col_{secrets.token_urlsafe(32)}"

def generate_enrollment_token() -> str:
    """Generate high-entropy, short-lived, single-use device enrollment token: ov_enroll_..."""
    return f"ov_enroll_{secrets.token_urlsafe(32)}"
