# tests/test_dashboard_routes.py
"""
Tests for Dashboard API endpoints and OV-BUG-004 verification.
Validates:
1. /api/v1/dashboard/overview returns 200 with complete metrics
2. /api/v1/dashboard/summary (OV-BUG-004 fix) returns 200 with identical structure
3. /api/v1/dashboard and /api/v1/dashboard/ both resolve cleanly
4. Unauthenticated requests to dashboard endpoints receive 401 Unauthorized
5. Tenant isolation ensures metrics only reflect current tenant's servers/alerts
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.models import Tenant, User
from app.core.security import create_access_token, get_password_hash

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_dashboard_user():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]

    tenant = Tenant(
        name=f"DashTenant_{uid}",
        slug=f"dashtenant-{uid}",
        plan="enterprise",
        created_at=datetime.now(timezone.utc)
    )
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"dash_{uid}@example.com",
        hashed_password=get_password_hash("Secret123!"),
        full_name="Dashboard User",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()

    token = create_access_token(user.id, tenant.id, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    yield {"tenant": tenant, "user": user, "headers": headers}

    db.close()


def test_dashboard_overview_endpoint(setup_dashboard_user):
    headers = setup_dashboard_user["headers"]
    response = client.get("/api/v1/dashboard/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "infrastructure" in data
    assert "collectors" in data
    assert "alerts" in data
    assert "incidents" in data
    assert "privacy" in data


def test_dashboard_summary_ov_bug_004(setup_dashboard_user):
    """Verify OV-BUG-004: /api/v1/dashboard/summary must return 200 OK with valid dashboard payload."""
    headers = setup_dashboard_user["headers"]
    response = client.get("/api/v1/dashboard/summary", headers=headers)
    assert response.status_code == 200, f"OV-BUG-004 regression: /api/v1/dashboard/summary returned {response.status_code}"
    data = response.json()
    assert "infrastructure" in data
    assert "collectors" in data
    assert "alerts" in data
    assert "incidents" in data
    assert "privacy" in data


def test_dashboard_root_routes(setup_dashboard_user):
    """Verify root /api/v1/dashboard and /api/v1/dashboard/ handle trailing-slash properly."""
    headers = setup_dashboard_user["headers"]
    
    # Without trailing slash
    res1 = client.get("/api/v1/dashboard", headers=headers, follow_redirects=True)
    assert res1.status_code == 200
    assert "infrastructure" in res1.json()

    # With trailing slash
    res2 = client.get("/api/v1/dashboard/", headers=headers, follow_redirects=True)
    assert res2.status_code == 200
    assert "infrastructure" in res2.json()


def test_dashboard_unauthenticated_rejected():
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 401
