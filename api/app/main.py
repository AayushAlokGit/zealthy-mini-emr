"""FastAPI application factory."""
import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .logging_setup import get_logger, setup_logging
from .routers import appointments, auth, lookups, me, patients, prescriptions
from .seed import seed_if_empty

setup_logging()
log = get_logger("app")
request_log = get_logger("request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Zealthy API (log_level=%s)...", settings.log_level)
    init_db()
    log.info("Database ready.")
    if settings.seed_on_startup:
        seed_if_empty()
    log.info("Startup complete; accepting requests.")
    yield
    log.info("Shutting down.")


app = FastAPI(title="Zealthy Mini-EMR API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with a correlation id, status, and latency.

    The id is echoed in the ``X-Request-ID`` response header so a client error
    can be traced to its server log line.
    """
    if request.url.path == "/api/health":
        return await call_next(request)  # skip noisy health-check polling

    rid = uuid4().hex[:8]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        request_log.exception(
            "rid=%s %s %s -> unhandled error (%.0fms)", rid, request.method, request.url.path, elapsed
        )
        raise

    elapsed = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = rid
    # 5xx -> ERROR, 4xx -> WARNING, else INFO.
    level = (
        logging.ERROR
        if response.status_code >= 500
        else logging.WARNING
        if response.status_code >= 400
        else logging.INFO
    )
    request_log.log(
        level,
        "rid=%s %s %s -> %s (%.0fms)",
        rid,
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(prescriptions.router)
app.include_router(lookups.router)
app.include_router(me.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
