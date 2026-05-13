"""
SupplyMind backend application entry point.

This module creates and configures the FastAPI application. It wires together
configuration, logging, middleware, routes, and lifecycle events.

The application factory pattern (`create_app`) makes the app testable —
tests can create isolated app instances with overridden dependencies.

Usage:
    Development (auto-reload):
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    Production:
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import (
    bind_correlation_id,
    clear_context,
    get_logger,
    setup_logging,
)


# ==============================================================================
# Lifecycle Management
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Code before `yield` runs at startup; code after `yield` runs at shutdown.
    Use this for resource initialization and cleanup that needs to happen
    once per application lifecycle, not once per request.
    """
    # Initialize logging as early as possible
    setup_logging()
    logger = get_logger(__name__)

    # Log startup with full configuration context
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        log_level=settings.log_level,
        log_format=settings.log_format,
        api_host=settings.api_host,
        api_port=settings.api_port,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
    )

    # Warn about insecure defaults in non-development environments
    if not settings.is_development and settings.is_using_default_secrets:
        logger.warning(
            "default_secrets_detected",
            message="API key or JWT secret is still a placeholder. "
                    "Set API_KEY and JWT_SECRET via .env or environment.",
        )

    logger.info("application_ready")

    # Yield control to FastAPI; the app runs until shutdown signal
    yield

    # Shutdown — clean up resources
    logger.info("application_shutting_down")
    # Future cleanup: close DB connections, flush metrics, etc.
    logger.info("application_stopped")


# ==============================================================================
# Prometheus Metrics
# ==============================================================================
# Define metrics at module level so they're created once at import time,
# not on every request. Each metric is a globally-accessible counter or
# histogram that handlers update.

# Track total HTTP requests with labels for method, endpoint, and status
http_requests_total = Counter(
    "supplymind_http_requests_total",
    "Total number of HTTP requests processed",
    labelnames=["method", "endpoint", "status"],
)

# Track HTTP request duration as a histogram
http_request_duration_seconds = Histogram(
    "supplymind_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# ==============================================================================
# Middleware
# ==============================================================================


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a correlation ID to every request.

    The ID is read from the X-Correlation-ID header if present (allowing
    upstream services to provide one), otherwise generated as a UUID.
    The ID is bound to the logging context and returned in the response
    header so clients can correlate their own logs with ours.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check for an incoming correlation ID, generate one if absent
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Bind to logging context for the duration of this request
        bind_correlation_id(correlation_id)

        try:
            response = await call_next(request)
        finally:
            # Ensure context is cleared even if the handler raised an exception
            clear_context()

        # Echo the correlation ID back so clients can use it
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records Prometheus metrics for every HTTP request.

    Tracks request count by status code and request duration as a histogram.
    The /metrics endpoint itself is excluded to avoid recursive measurement.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Don't track the metrics endpoint itself (avoids self-reference noise)
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        # Use the route template, not the full URL, to avoid high cardinality
        endpoint = request.url.path

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time
            http_requests_total.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()
            http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

        return response


# ==============================================================================
# Application Factory
# ==============================================================================


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory pattern makes the app testable — tests can build isolated
    app instances with mocked dependencies. Production code calls this once
    at module load time to produce the `app` global.

    Returns:
        Configured FastAPI application ready to serve requests.
    """
    app = FastAPI(
        title="SupplyMind API",
        description=(
            "Autonomous multi-agent AI platform for supply chain intelligence. "
            "Monitors suppliers, detects anomalies, generates recommendations, "
            "and produces executive briefings."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        # OpenAPI documentation endpoints
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — must come before correlation ID and metrics middleware so it
    # processes preflight requests before they hit those middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Order matters: correlation ID must run before metrics so logged
    # metric events include the correlation ID
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(MetricsMiddleware)

    return app

# ==============================================================================
# Application Instance
# ==============================================================================
# Create the app at module load time. Uvicorn imports this `app` variable
# and serves it.

app = create_app()
logger = get_logger(__name__)


# ==============================================================================
# Health Check Endpoints
# ==============================================================================
# Health checks are used by Docker, Kubernetes, and load balancers to
# determine if the container is alive and ready to serve traffic.


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Basic liveness check.

    Returns 200 OK if the application process is responding. This is the
    minimum signal that the container hasn't crashed. Used by Docker's
    HEALTHCHECK directive and Kubernetes liveness probes.

    Does not check downstream dependencies — see /health/ready for that.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health/ready", tags=["health"])
async def readiness_check() -> dict[str, object]:
    """
    Readiness check — verifies the application is ready to serve traffic.

    Returns 200 OK only if all critical dependencies are reachable. Used by
    Kubernetes readiness probes to know when to send traffic to a pod.

    Currently checks: configuration loaded successfully.
    Future checks: ChromaDB connection, model availability, downstream APIs.
    """
    checks: dict[str, bool] = {
        "config_loaded": True,
        # Future: "chromadb_reachable": check_chromadb(),
        # Future: "model_loaded": check_model_loaded(),
    }

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "checks": checks,
    }


# ==============================================================================
# Root Endpoint
# ==============================================================================


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """
    Root endpoint — basic application identification.

    Returns minimal application metadata. Useful for verifying the API
    is reachable and identifying which version is deployed.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ==============================================================================
# Prometheus Metrics Endpoint
# ==============================================================================
# This endpoint is what Prometheus scrapes every 15 seconds to collect
# metrics. Returns the current state of all registered metrics in
# Prometheus's text exposition format.


@app.get("/metrics", tags=["observability"])
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns all registered metrics in the Prometheus text exposition format.
    Scraped by Prometheus every 15 seconds (configured in prometheus.yml).

    Excluded from this endpoint's own metrics to avoid recursive measurement.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

# ==============================================================================
# Direct Execution Entrypoint
# ==============================================================================
# When this module is run directly (python -m app.main), launch Uvicorn
# programmatically. In containers, Uvicorn is invoked from the Dockerfile's
# CMD, so this block is for local development convenience.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        workers=settings.api_workers if not settings.is_development else 1,
        log_config=None,  # We configure logging ourselves
        access_log=False,  # Disable Uvicorn's access logs; use ours via middleware
    )