# backend/app/api/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.models.models import User, Tenant
from app.schemas.schemas import LoginRequest, TokenResponse, UserOut
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    tenant_name = tenant.name if tenant else "Default Organization"

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        role=user.role,
        email=user.email,
        full_name=user.full_name
    )

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@router.post("/logout")
def logout():
    # Client will clear JWT; API confirms safe session termination
    return {"status": "success", "message": "Logged out successfully"}
