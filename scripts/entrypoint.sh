#!/bin/sh
set -eu

# Where Cloud Run/Docker bind the bucket/volume
PERSIST_DIR="/data"
PERSIST_DB="${PERSIST_DIR}/qms.sqlite"

# Where the app actually reads/writes the DB (local ephemeral disk)
RUNTIME_DB="/tmp/qms.sqlite"

echo "[entrypoint] Persist dir: ${PERSIST_DIR}"
echo "[entrypoint] Persist DB : ${PERSIST_DB}"
echo "[entrypoint] Runtime DB : ${RUNTIME_DB}"

# Ensure dirs exist
mkdir -p "${PERSIST_DIR}" /tmp

# --- Startup sync: copy persisted DB into runtime if present
if [ -f "${PERSIST_DB}" ]; then
  echo "[entrypoint] Found persisted DB, copying to runtime..."
  cp -f "${PERSIST_DB}" "${RUNTIME_DB}"
else
  echo "[entrypoint] No persisted DB found. A new DB will be created at runtime."
fi

# --- Launch app (point it to runtime DB)
export QMS_DB_PATH="${RUNTIME_DB}"
SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-1800}"  # default 30 minutes

echo "[entrypoint] Starting uvicorn on port ${PORT:-8080}..."
uvicorn qminesweeper.webapp:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers "${UVICORN_WORKERS:-1}" \
  --proxy-headers &
PID=$!

# Periodic sync (optional): copy runtime -> persisted every SYNC_INTERVAL_SECONDS
sync_loop() {
  # If interval <= 0, skip periodic sync completely
  if [ "${SYNC_INTERVAL_SECONDS}" -le 0 ] 2>/dev/null; then
    echo "[entrypoint] Periodic sync disabled."
    return
  fi

  echo "[entrypoint] Periodic sync every ${SYNC_INTERVAL_SECONDS}s."
  while kill -0 "$PID" 2>/dev/null; do
    # Sleep first so we don't immediately sync on startup
    sleep "${SYNC_INTERVAL_SECONDS}" || true
    # If the app is already gone, stop
    kill -0 "$PID" 2>/dev/null || break
    # Perform sync only if DB exists and is non-empty
    if [ -s "${RUNTIME_DB}" ]; then
      cp -f "${RUNTIME_DB}" "${PERSIST_DB}"
      # Ensure data hits the mount
      sync
      echo "[entrypoint] Periodic sync: ${RUNTIME_DB} -> ${PERSIST_DB}"
    fi
  done
}

sync_loop &
SYNC_PID=$!

# --- Shutdown trap: final sync back to persisted path
cleanup() {
  echo "[entrypoint] Caught shutdown, syncing DB back to persisted storage..."
  if [ -s "${RUNTIME_DB}" ]; then
    cp -f "${RUNTIME_DB}" "${PERSIST_DB}"
    sync
  fi
  kill -TERM "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  kill "$SYNC_PID" 2>/dev/null || true
}
trap cleanup TERM INT

wait "$PID"
