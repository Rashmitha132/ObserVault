# backend/app/core/rbac.py
"""
ObserVault Enterprise Role-Based Access Control (RBAC).
Provides explicit permission matrices, role hierarchies, and route security decorators.
"""

from enum import Enum
from typing import Set, List
from fastapi import HTTPException, status, Depends
from app.models.models import User
from app.api.deps import get_current_user

class Role(str, Enum):
    ORG_ADMIN = "org_admin"
    SECURITY_ANALYST = "security_analyst"
    DEVOPS_ENGINEER = "devops_engineer"
    READ_ONLY_VIEWER = "read_only_viewer"

class Permission(str, Enum):
    # Infrastructure
    INFRA_VIEW = "infra:view"
    INFRA_MANAGE = "infra:manage"
    
    # Security & Privacy
    SECURITY_VIEW = "security:view"
    SECURITY_MANAGE = "security:manage"
    PRIVACY_VIEW = "privacy:view"
    PRIVACY_AUDIT = "privacy:audit"
    
    # Collector Management
    COLLECTORS_VIEW = "collectors:view"
    COLLECTORS_MANAGE = "collectors:manage"
    
    # Incidents & Alerts
    INCIDENTS_VIEW = "incidents:view"
    INCIDENTS_ACKNOWLEDGE = "incidents:acknowledge"
    INCIDENTS_RESOLVE = "incidents:resolve"
    
    # Recommendations
    RECOMMENDATIONS_VIEW = "recommendations:view"
    RECOMMENDATIONS_ACT = "recommendations:act"
    
    # Tenant & Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_MANAGE = "settings:manage"
    USERS_MANAGE = "users:manage"

# Explicit role permission mappings
ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    Role.ORG_ADMIN: {p for p in Permission},
    Role.SECURITY_ANALYST: {
        Permission.INFRA_VIEW,
        Permission.SECURITY_VIEW,
        Permission.SECURITY_MANAGE,
        Permission.PRIVACY_VIEW,
        Permission.PRIVACY_AUDIT,
        Permission.COLLECTORS_VIEW,
        Permission.INCIDENTS_VIEW,
        Permission.INCIDENTS_ACKNOWLEDGE,
        Permission.RECOMMENDATIONS_VIEW,
        Permission.RECOMMENDATIONS_ACT,
        Permission.SETTINGS_VIEW
    },
    Role.DEVOPS_ENGINEER: {
        Permission.INFRA_VIEW,
        Permission.INFRA_MANAGE,
        Permission.COLLECTORS_VIEW,
        Permission.COLLECTORS_MANAGE,
        Permission.INCIDENTS_VIEW,
        Permission.INCIDENTS_ACKNOWLEDGE,
        Permission.INCIDENTS_RESOLVE,
        Permission.RECOMMENDATIONS_VIEW,
        Permission.RECOMMENDATIONS_ACT,
        Permission.PRIVACY_VIEW,
        Permission.SETTINGS_VIEW
    },
    Role.READ_ONLY_VIEWER: {
        Permission.INFRA_VIEW,
        Permission.SECURITY_VIEW,
        Permission.PRIVACY_VIEW,
        Permission.COLLECTORS_VIEW,
        Permission.INCIDENTS_VIEW,
        Permission.RECOMMENDATIONS_VIEW,
        Permission.SETTINGS_VIEW
    }
}

# Compatibility mapping for legacy Phase 1 roles
LEGACY_ROLE_MAP = {
    "admin": Role.ORG_ADMIN,
    "engineer": Role.DEVOPS_ENGINEER,
    "viewer": Role.READ_ONLY_VIEWER,
    "analyst": Role.SECURITY_ANALYST
}

def resolve_role(role_str: str) -> str:
    """Normalizes role strings from either legacy or modern format."""
    normalized = role_str.lower().strip()
    return LEGACY_ROLE_MAP.get(normalized, normalized)

def has_permission(user_role: str, permission: Permission) -> bool:
    """Evaluates whether a role possesses a specific permission."""
    canonical_role = resolve_role(user_role)
    perms = ROLE_PERMISSIONS.get(canonical_role, set())
    return permission in perms

class RequirePermissions:
    """
    FastAPI dependency factory enforcing required permissions on endpoints.
    """
    def __init__(self, required: List[Permission]):
        self.required = required

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        canonical_role = resolve_role(current_user.role)
        perms = ROLE_PERMISSIONS.get(canonical_role, set())
        missing = [p.value for p in self.required if p not in perms]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission(s): {', '.join(missing)}"
            )
        return current_user
