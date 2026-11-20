# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# For SQLite, enable check_same_thread=False
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def patch_database_schema(target_engine):
    """Safely apply idempotent column and schema upgrades for SQLite/PostgreSQL."""
    try:
        with target_engine.connect() as conn:
            # Check collectors table columns
            result = conn.exec_driver_sql("PRAGMA table_info(collectors)")
            existing_cols = {row[1] for row in result.fetchall()}
            
            if existing_cols:  # table exists
                col_defs = [
                    ("os_type", "VARCHAR(50) DEFAULT 'windows'"),
                    ("os_version", "VARCHAR(100)"),
                    ("environment", "VARCHAR(50) DEFAULT 'production'"),
                    ("enrollment_status", "VARCHAR(30) DEFAULT 'active'"),
                    ("is_revoked", "BOOLEAN DEFAULT 0"),
                    ("revoked_at", "DATETIME"),
                    ("revoked_by", "VARCHAR(100)")
                ]
                for col_name, col_type in col_defs:
                    if col_name not in existing_cols:
                        conn.exec_driver_sql(f"ALTER TABLE collectors ADD COLUMN {col_name} {col_type}")
                conn.commit()
    except Exception as e:
        print(f"[Schema Patch Warning]: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
