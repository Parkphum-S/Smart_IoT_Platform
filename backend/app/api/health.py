"""Health check endpoints for application monitoring."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Application liveness check")
async def health_check() -> dict[str, str]:
    """Report whether the API process is running."""
    return {"status": "healthy"}


@router.get("/health/ready", summary="Application readiness check")
async def readiness_check(request: Request):
    """Check whether the application can reach its database."""
    session_factory = request.app.state.db_session_factory

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unavailable"},
        )

    return {"status": "ready", "database": "connected"}
