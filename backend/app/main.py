# backend/app/main.py
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.database import engine, Base
from app.api import (
    auth,
    telemetry,
    heartbeat,
    dashboard,
    infrastructure,
    network,
    security_events,
    alerts,
    incidents,
    collectors,
    egress,
    recommendations,
    tenant,
    simulator,
    security_hardening,
    traces,
    ml_detection,
    rca,
    predictive,
    integrations,
    ai
)

# Initialize database schema and ensure seed data is present
from app.core.database import patch_database_schema
Base.metadata.create_all(bind=engine)
patch_database_schema(engine)
try:
    from app.seed import seed_database
    seed_database()
except Exception as e:
    print(f"[Startup Seed Notice]: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ObserVault SaaS Observability Platform - Secure, Privacy-First, Automated Intelligence"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Validation Error Handler: Explicitly highlights forbidden/unapproved field rejections
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # Check if extra forbidden fields were detected
    extra_field_errors = [e for e in errors if e.get("type") == "extra_forbidden"]
    if extra_field_errors:
        forbidden_fields = [str(e.get("loc", [-1])[-1]) for e in extra_field_errors]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "PrivacyAllowlistViolation",
                "message": f"Rejected unapproved fields: {forbidden_fields}. ObserVault requires all outbound telemetry to strictly conform to the approved metadata allow-list.",
                "details": errors
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "ValidationError", "details": errors}
    )

# Register API v1 Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(telemetry.router, prefix=f"{settings.API_V1_STR}/telemetry", tags=["Telemetry Ingestion"])
app.include_router(heartbeat.router, prefix=f"{settings.API_V1_STR}/heartbeat", tags=["Collector Heartbeat"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"])
app.include_router(infrastructure.router, prefix=f"{settings.API_V1_STR}/infrastructure", tags=["Infrastructure"])
app.include_router(network.router, prefix=f"{settings.API_V1_STR}/network", tags=["Network Observability"])
app.include_router(security_events.router, prefix=f"{settings.API_V1_STR}/security-events", tags=["Security Events"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Alerts"])
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["Incidents"])
app.include_router(collectors.router, prefix=f"{settings.API_V1_STR}/collectors", tags=["Collectors"])
app.include_router(egress.router, prefix=f"{settings.API_V1_STR}/egress", tags=["Privacy & Egress Audit"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recommendations", tags=["Recommendations"])
app.include_router(tenant.router, prefix=f"{settings.API_V1_STR}/tenant", tags=["Tenant Settings"])
app.include_router(simulator.router, prefix=f"{settings.API_V1_STR}/simulator", tags=["Demo Simulator"])
app.include_router(security_hardening.router, prefix=f"{settings.API_V1_STR}/security-hardening", tags=["Security Hardening"])
app.include_router(traces.router, prefix="/api", tags=["OpenTelemetry Tracing"])
app.include_router(ml_detection.router, prefix="/api", tags=["Machine Learning Anomaly Detection"])
app.include_router(rca.router, prefix="/api", tags=["Root Cause Analysis (RCA)"])
app.include_router(predictive.router, prefix="/api", tags=["Predictive Analytics & Capacity Forecasting"])
app.include_router(integrations.router, prefix="/api", tags=["Real Infrastructure Integrations"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI Intelligence Layer"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Intelligence Layer"])

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ObserVault SaaS Backend",
        "version": settings.VERSION,
        "privacy_enforcement": "strict_allowlist_active"
    }
