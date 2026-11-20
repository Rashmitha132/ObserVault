# tests/test_tenant_isolation.py
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.core.database import SessionLocal
from app.models.models import Tenant, User, Server, Alert, Collector
from app.core.security import create_access_token, decode_access_token

def test_tenant_isolation():
    db = SessionLocal()
    try:
        acme = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
        biohealth = db.query(Tenant).filter(Tenant.slug == "biohealth").first()

        assert acme is not None, "Acme tenant must exist"
        assert biohealth is not None, "BioHealth tenant must exist"
        assert acme.id != biohealth.id

        # 1. Server isolation
        acme_servers = db.query(Server).filter(Server.tenant_id == acme.id).all()
        bio_servers = db.query(Server).filter(Server.tenant_id == biohealth.id).all()

        acme_server_ids = {s.id for s in acme_servers}
        bio_server_ids = {s.id for s in bio_servers}

        assert len(acme_servers) > 0
        assert len(bio_servers) > 0
        # Check strict disjoint sets
        assert acme_server_ids.isdisjoint(bio_server_ids)

        # 2. Collector isolation
        acme_collectors = db.query(Collector).filter(Collector.tenant_id == acme.id).all()
        bio_collectors = db.query(Collector).filter(Collector.tenant_id == biohealth.id).all()

        acme_col_ids = {c.id for c in acme_collectors}
        bio_col_ids = {c.id for c in bio_collectors}

        assert acme_col_ids.isdisjoint(bio_col_ids)

        # 3. User JWT Claims Isolation
        acme_user = db.query(User).filter(User.tenant_id == acme.id).first()
        bio_user = db.query(User).filter(User.tenant_id == biohealth.id).first()

        acme_token = create_access_token(acme_user.id, acme.id, acme_user.role)
        bio_token = create_access_token(bio_user.id, biohealth.id, bio_user.role)

        payload_acme = decode_access_token(acme_token)
        payload_bio = decode_access_token(bio_token)

        assert payload_acme["tenant_id"] == acme.id
        assert payload_bio["tenant_id"] == biohealth.id
        assert payload_acme["tenant_id"] != payload_bio["tenant_id"]

    finally:
        db.close()
