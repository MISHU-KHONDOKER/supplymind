# ==============================================================================
# SupplyMind Backend — Multi-Stage Production Dockerfile
# ==============================================================================
# Stage 1 (builder): installs dependencies into a virtual environment
# Stage 2 (runtime): copies only the venv and source code into a minimal image
#
# Build:   docker build -t supplymind-backend:latest .
# Run:     docker run -p 8000:8000 supplymind-backend:latest
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
# This stage has build tools (gcc, headers) needed to compile some packages.
# It produces a /opt/venv directory we'll copy into the runtime stage.

FROM python:3.11-slim AS builder

# Set working directory inside the container
WORKDIR /build

# Install build dependencies needed to compile packages with native extensions
# (cryptography, psycopg2, numpy, etc.). build-essential includes gcc and make.
# Cleanup in same RUN to keep layer small.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment inside the builder.
# Using a venv (instead of system Python) makes copying to the runtime stage trivial.
RUN python -m venv /opt/venv

# Activate the venv by prepending it to PATH for all subsequent commands.
# Once PATH points to /opt/venv/bin, every `python` and `pip` runs inside the venv.
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip first — modern pip has better dependency resolution
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements file separately from source code.
# This is a layer caching optimization: if requirements.txt doesn't change,
# Docker reuses the cached pip install layer on subsequent builds.
COPY requirements.txt .

# Install all dependencies into the venv.
# --no-cache-dir keeps the image smaller by not storing pip's download cache.
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Runtime
# ------------------------------------------------------------------------------
# This stage is the actual production image. It contains:
#   - Python runtime
#   - The pre-built virtual environment from Stage 1
#   - Application source code
#   - A non-root user for security
# It does NOT contain build tools, gcc, or pip caches.

FROM python:3.11-slim AS runtime

# Metadata labels — useful for image inspection and registry filtering
LABEL maintainer="Mohyminul Islam <sailormishu50@gmail.com>"
LABEL project="supplymind"
LABEL component="backend"
LABEL description="SupplyMind multi-agent supply chain intelligence backend"

# Set Python to unbuffered output mode.
# Without this, print() and logging go through Python's IO buffer and may
# not appear in `docker logs` until the buffer fills. Critical for observability.
ENV PYTHONUNBUFFERED=1

# Disable pip's automatic version check on startup
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Don't write .pyc bytecode files — they're regeneratable and just clutter the image
ENV PYTHONDONTWRITEBYTECODE=1

# Make Python find packages from the venv automatically
ENV PATH="/opt/venv/bin:$PATH"

# Install only the runtime system dependencies (no build tools).
# tini provides proper signal handling — critical for graceful shutdowns.
# curl is used by the HEALTHCHECK directive below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group for running the application.
# Running as root inside a container is a security risk: if the container is
# compromised, the attacker has root privileges that can sometimes escape.
RUN groupadd --system --gid 1001 supplymind && \
    useradd --system --uid 1001 --gid supplymind --create-home --shell /bin/bash supplymind

# Copy the pre-built virtual environment from the builder stage.
# This is the multi-stage magic: we get all dependencies without any build tools.
COPY --from=builder --chown=supplymind:supplymind /opt/venv /opt/venv

# Set the working directory for the application
WORKDIR /app

# Copy application source code with correct ownership.
# Doing this after dependency installation maximizes Docker layer caching:
# code changes invalidate this layer but not the (much slower) dependency layer.
COPY --chown=supplymind:supplymind ./app /app/app

# Create directories the application writes to, with correct ownership
RUN mkdir -p /app/data /app/logs /app/eval_outputs && \
    chown -R supplymind:supplymind /app

# Switch to the non-root user for everything that follows.
# All processes inside the container will run as `supplymind` (uid 1001).
USER supplymind

# Document which port the application listens on.
# EXPOSE is informational only; it doesn't actually publish the port.
EXPOSE 8000

# Health check — Docker uses this to determine container health.
# Kubernetes and orchestration tools use this for liveness/readiness probes.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Use tini as PID 1 — it forwards signals properly and reaps zombie processes.
# Without tini, Python becomes PID 1 and doesn't handle SIGTERM correctly,
# causing slow or broken graceful shutdowns.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command — runs the FastAPI app with Uvicorn.
# In production, you'd override this to add --workers based on CPU count.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

