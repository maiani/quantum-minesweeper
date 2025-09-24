#!/bin/sh
set -eu

DB_PATH="/data/qms.sqlite"

# Ensure /data exists (for Docker and Cloud Run)
mkdir -p /data

# --- 1. Sync from GCS if configured ---
if [ -n "${GCS_BUCKET:-}" ]; then
    echo "[entrypoint] Syncing database from GCS bucket: gs://${GCS_BUCKET}/qms.sqlite"
    if gsutil ls "gs://${GCS_BUCKET}/qms.sqlite" >/dev/null 2>&1; then
        gsutil cp "gs://${GCS_BUCKET}/qms.sqlite" "$DB_PATH"
    else
        echo "[entrypoint] No DB found in GCS, starting fresh."
    fi
else
    echo "[entrypoint] No GCS_BUCKET set → running with local /data volume or fallback."
fi

# --- 2. Run app ---
echo "[entrypoint] Starting uvicorn..."
uvicorn qminesweeper.webapp:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --proxy-headers &

PID=$!

# --- 3. Sync back to GCS on shutdown ---
trap 'echo "[entrypoint] Caught shutdown signal, syncing DB..."; 
      if [ -n "${GCS_BUCKET:-}" ]; then
          gsutil cp "$DB_PATH" "gs://${GCS_BUCKET}/qms.sqlite"
      fi
      kill -TERM $PID; wait $PID' TERM INT

wait $PID
