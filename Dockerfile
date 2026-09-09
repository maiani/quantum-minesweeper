# syntax=docker/dockerfile:1.7

############################
# Builder: build only our wheel
############################
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
   && rm -rf /var/lib/apt/lists/*

# Not /src: the project keeps its packages in a directory of that name, and
# "COPY src /src/src" is needlessly hard to read.
WORKDIR /build

# Install build tools once (cached unless pyproject changes)
COPY pyproject.toml README.md ./
RUN python -m pip install --upgrade pip setuptools wheel build

COPY src ./src
RUN python -m build --wheel --outdir /wheels

############################
# Final: slim runtime image
############################
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Install app + deps from wheel
COPY --from=builder /wheels /wheels
RUN python -m pip install --upgrade pip \
 && wheel="$(ls /wheels/*.whl)" \
 && pip install --no-cache-dir "${wheel}[stim]" \
 && rm -rf /wheels

# Create /data with proper ownership for SQLite DB
RUN mkdir -p /data && chown -R 10001:10001 /data

# Copy entrypoint
COPY --chmod=755 scripts/entrypoint.sh /entrypoint.sh

# Runtime user (non-root)
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Expose same port as entrypoint (Cloud Run will override PORT anyway)
EXPOSE 8080
ENV PORT=8080

ENTRYPOINT ["/entrypoint.sh"]
