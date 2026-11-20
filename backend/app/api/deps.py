# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token, hash_token
from app.models.models import User, Collector, Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims",
        )
    
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )
    return user

def get_current_collector(
    x_collector_key: str = Header(..., alias="X-Collector-Key"),
    db: Session = Depends(get_db)
) -> Collector:
    if not x_collector_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Collector API Key required (X-Collector-Key header)",
        )
    
    key_hash = hash_token(x_collector_key)
    collector = db.query(Collector).filter(Collector.token_hash == key_hash).first()
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Collector credentials",
        )
    
    # Check if collector has been revoked (Phase 2F device lifecycle security)
    if getattr(collector, "is_revoked", False) or getattr(collector, "enrollment_status", "") == "revoked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collector has been revoked. Access denied.",
        )
    
    # Verify associated tenant exists and is active
    tenant = db.query(Tenant).filter(Tenant.id == collector.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collector tenant inactive or not found",
        )
    
    return collector
