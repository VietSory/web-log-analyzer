from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
from pathlib import Path
from time import perf_counter
import re
import sqlite3
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from core.observability import configure_observability
from core.rate_limit import InMemoryRateLimiter, RateLimitDecision
from core.report_store import init_report_store
from database import get_db_connection, init_db
from routers import analyze, auth, history, servers, stats, upload


settings = get_settings()
logger = logging.getLogger("web_log_analyzer.http")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_rate_limiter = InMemoryRateLimiter()


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    key: str
    limit: int
    disclose_quota: bool


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    init_report_store()
    try:
        yield
    finally:
        telemetry_runtime.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

telemetry_runtime = configure_observability(
    app,
    enabled=settings.otel_enabled,
    service_name=settings.otel_service_name,
)


def _rate_limit_policy(request: Request) -> RateLimitPolicy | None:
    if not settings.rate_limit_enabled:
        return None
    if request.method == "OPTIONS" or request.url.path.startswith("/health/"):
        return None

    client_host = request.client.host if request.client else "unknown"
    if request.url.path.startswith("/api/auth/"):
        return RateLimitPolicy(
            key=f"auth:{client_host}",
            limit=settings.auth_rate_limit_requests,
            disclose_quota=False,
        )
    return RateLimitPolicy(
        key=f"api:{client_host}",
        limit=settings.rate_limit_requests,
        disclose_quota=True,
    )


def _rate_limit_headers(decision: RateLimitDecision) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
    }


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_request_id
        if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
        else str(uuid4())
    )
    request.state.request_id = request_id
    started_at = perf_counter()

    policy = _rate_limit_policy(request)
    decision: RateLimitDecision | None = None
    if policy is not None:
        decision = _rate_limiter.check(
            policy.key,
            limit=policy.limit,
            window_seconds=settings.rate_limit_window_seconds,
        )
        if not decision.allowed:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.warning(
                "request_rate_limited method=%s path=%s request_id=%s duration_ms=%s",
                request.method,
                request.url.path,
                request_id,
                duration_ms,
            )
            headers = {"X-Request-ID": request_id}
            if policy.disclose_quota:
                headers.update(_rate_limit_headers(decision))
                headers["Retry-After"] = str(decision.retry_after_seconds)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests", "request_id": request_id},
                headers=headers,
            )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request_failed method=%s path=%s request_id=%s duration_ms=%s",
            request.method,
            request.url.path,
            request_id,
            duration_ms,
        )
        raise

    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    if decision is not None and policy is not None and policy.disclose_quota:
        for header_name, header_value in _rate_limit_headers(decision).items():
            response.headers[header_name] = header_value

    logger.info(
        "request_complete method=%s path=%s status=%s request_id=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
        duration_ms,
    )
    return response


@app.get("/health/live", tags=["Health"])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
def readiness():
    database_status = "ready"
    try:
        connection = get_db_connection()
        try:
            connection.execute("SELECT 1").fetchone()
        finally:
            connection.close()
    except (sqlite3.Error, OSError):
        logger.exception("readiness database check failed")
        database_status = "unavailable"

    model_metadata = Path(settings.model_dir) / "metadata.json"
    model_status = "ready" if model_metadata.is_file() else "unavailable"

    body = {
        "status": "ready" if database_status == "ready" else "not_ready",
        "components": {
            "database": database_status,
            "ml_model": model_status,
            "telemetry": "enabled" if telemetry_runtime.enabled else "disabled",
        },
    }
    if database_status != "ready":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body,
        )
    return body


app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(stats.router, prefix="/api", tags=["Stats"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(servers.router, prefix="/api", tags=["Servers"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )
