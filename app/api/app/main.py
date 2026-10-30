import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.health import router as health_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.observability import router as observability_router
from app.api.v1.rfqs import router as rfq_router
from app.api.v1.suppliers import router as supplier_router
from app.api.v1.workflow import router as workflow_router
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def _error_body(
    request: Request,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    request_id = getattr(request.state, "request_id", None)
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }
    }


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="SourcingIQ API", version="0.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_t = time.perf_counter()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_t) * 1000, 2)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "event_type": "http.request",
                "outcome": str(response.status_code),
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            503: "UNAVAILABLE",
        }.get(exc.status_code, "HTTP_ERROR")
        message = (
            exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, code, message),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled error",
            extra={"event_type": "http.error", "outcome": type(exc).__name__},
        )
        return JSONResponse(
            status_code=500,
            content=_error_body(request, "INTERNAL_ERROR", "The request could not be completed."),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, str]] = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"] if part != "body")
            message = str(error["msg"])
            if message.startswith("Value error, "):
                message = message.removeprefix("Value error, ")
            if message == "Field required":
                message = "This field is required."
            details.append({"field": field, "issue": message})
        return JSONResponse(
            status_code=422,
            content=_error_body(
                request,
                "VALIDATION_ERROR",
                "The request is invalid.",
                details,
            ),
        )

    app.include_router(health_router)
    app.include_router(rfq_router, prefix="/api/v1")
    app.include_router(supplier_router, prefix="/api/v1")
    app.include_router(workflow_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(evaluations_router, prefix="/api/v1")
    app.include_router(observability_router, prefix="/api/v1")
    return app


app = create_app()
