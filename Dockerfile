# syntax=docker/dockerfile:1.7

############################
# Builder: produce wheels
############################
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
   && rm -rf /var/lib/apt/lists/*

WORKDIR /src
# Copy only what's needed to resolve & build
COPY pyproject.toml README.md /src/
COPY qminesweeper /src/qminesweeper

# Build wheels for app + ALL deps (qiskit, stim, etc.)
RUN python -m pip install --upgrade pip setuptools wheel \
 && python -m pip wheel --wheel-dir /wheels /src

############################
# Final: slim runtime image
############################
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Install from prebuilt wheels (no compilers needed here)
COPY --from=builder /wheels /wheels
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

# Runtime user (non-root)
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Basic Auth defaults (override in deploy)
ENV DEMO_USER=demo \
    DEMO_PASS=nordita

EXPOSE 8080
# Respect Cloud Run's $PORT; 1 worker fits 1 vCPU
CMD ["sh","-c","uvicorn qminesweeper.webapp:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers"]
