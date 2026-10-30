from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.db import get_engine
from app.services.health import check_readiness

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> JSONResponse:
    report = check_readiness(get_engine())
    return JSONResponse(status_code=200 if report.ok else 503, content=report.as_dict())
