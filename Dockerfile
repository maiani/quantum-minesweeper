# syntax=docker/dockerfile:1.7

############################
# Builder: build only our wheel
############################
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
   && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Install build tools once (cached unless pyproject changes)
COPY pyproject.toml README.md /src/
RUN python -m pip install --upgrade pip setuptools wheel build

COPY qminesweeper /src/qminesweeper
RUN python -m build --wheel --outdir /wheels

############################
# Final: slim runtime image
############################
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Install app + deps directly from PyPI wheels
COPY --from=builder /wheels /wheels
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir /wheels/*.whl \
 && rm -rf /wheels

# Runtime user (non-root)
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
CMD ["sh","-c","uvicorn qminesweeper.webapp:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers"]
