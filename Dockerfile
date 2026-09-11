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
COPY pyproject.toml README.md LICENSE ./
RUN python -m pip install --upgrade pip setuptools wheel build

COPY src ./src
RUN python -m build --wheel --outdir /wheels

############################
# Browser bundle: the installable PWA the server hands out at /app/
############################
FROM python:3.13-slim AS browser

ENV PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore
WORKDIR /build

# The build script imports the package and renders the shared Jinja templates,
# so it needs the project installed rather than just copied.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir .

# Reports go to this origin's own ingest route: QMS_BROWSER_ANALYTICS_URL
# defaults to the relative "/analytics", which keeps the bundle host-independent
# so the same image works on any domain without a rebuild.
RUN python scripts/build_browser.py

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

# The installable PWA, served read-only at /app/.
COPY --from=browser /build/dist /srv/pwa
ENV QMS_BROWSER_DIST_DIR=/srv/pwa

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
