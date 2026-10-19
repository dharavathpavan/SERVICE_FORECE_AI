from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.services.telephony.factory import get_adapter
from app.services.voice.factory import get_voice_provider
from app.services.storage.factory import get_storage

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Liveness probe: verifies that the HTTP server is responsive."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
    }


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe: validates database connectivity and core services."""
    checks = {
        "database": "unknown",
        "telephony_provider": settings.TELEPHONY_PROVIDER,
        "telephony_reachable": "unknown",
        "voice_provider": settings.VOICE_PROVIDER,
        "voice_configured": "unknown",
        "storage_backend": settings.STORAGE_BACKEND,
        "ai_provider": "configured" if settings.GEMINI_API_KEY else "simulation_mode",
    }

    is_ready = True

    # Database connectivity test
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        is_ready = False

    # Telephony connectivity is reported honestly; it does not fail readiness
    # (the API is still useful while a gateway is down), but it is never faked.
    try:
        conn = get_adapter().verify_connectivity()
        checks["telephony_reachable"] = "yes" if conn.ok else "no"
    except Exception as e:
        checks["telephony_reachable"] = f"error: {type(e).__name__}"

    try:
        checks["voice_configured"] = "yes" if get_voice_provider().is_configured() else "no"
    except Exception as e:
        checks["voice_configured"] = f"error: {type(e).__name__}"

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
