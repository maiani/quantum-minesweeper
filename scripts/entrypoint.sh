#!/bin/sh
set -eu

PERSIST_DIR="/data"
PERSIST_DB="${PERSIST_DIR}/qms.sqlite"

RUNTIME_DB="/tmp/qms.sqlite"
SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-1800}"  # 30 minutes default

echo "[entrypoint] Persist dir : ${PERSIST_DIR}"
echo "[entrypoint] Persist DB  : ${PERSIST_DB}"
echo "[entrypoint] Runtime DB  : ${RUNTIME_DB}"
mkdir -p "${PERSIST_DIR}" /tmp

copy_trio() {
  # $1 = src base, $2 = dst base
  for s in "" "-wal" "-shm"; do
    if [ -f "$1$s" ]; then
      cp -f "$1$s" "$2$s"
    else
      # keep destination clean if source side doesn't have this sidecar
      rm -f "$2$s" 2>/dev/null || true
    fi
  done
  sync
}

# --- Startup: pull latest persisted DB (trio) into runtime
if [ -f "${PERSIST_DB}" ] || [ -f "${PERSIST_DB}-wal" ]; then
  echo "[entrypoint] Restoring DB from persisted storage..."
  copy_trio "${PERSIST_DB}" "${RUNTIME_DB}"
else
  echo "[entrypoint] No persisted DB found. A new DB will be created."
fi

# --- Launch app using runtime DB
export QMS_DB_PATH="${RUNTIME_DB}"
echo "[entrypoint] Starting uvicorn on port ${PORT:-8080}..."
uvicorn qminesweeper.webapp:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers "${UVICORN_WORKERS:-1}" \
  --proxy-headers &
PID=$!

# --- Periodic sync from runtime -> persisted (optional)
sync_loop() {
  if [ "${SYNC_INTERVAL_SECONDS}" -le 0 ] 2>/dev/null; then
    echo "[entrypoint] Periodic sync disabled."
    return
  fi
  echo "[entrypoint] Periodic sync every ${SYNC_INTERVAL_SECONDS}s."
  while kill -0 "$PID" 2>/dev/null; do
    sleep "${SYNC_INTERVAL_SECONDS}" || true
    kill -0 "$PID" 2>/dev/null || break
    if [ -s "${RUNTIME_DB}" ] || [ -s "${RUNTIME_DB}-wal" ]; then
      echo "[entrypoint] Periodic sync: runtime -> persisted"
      copy_trio "${RUNTIME_DB}" "${PERSIST_DB}"
    fi
  done
}
sync_loop &
SYNC_PID=$!

# --- Graceful shutdown: stop app (closing DB), then final sync
cleanup() {
  echo "[entrypoint] Shutdown: stopping app and syncing DB..."
  kill -TERM "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  if [ -f "${RUNTIME_DB}" ] || [ -f "${RUNTIME_DB}-wal" ]; then
    copy_trio "${RUNTIME_DB}" "${PERSIST_DB}"
    echo "[entrypoint] Final sync complete."
  fi
  kill "$SYNC_PID" 2>/dev/null || true
}
trap cleanup TERM INT

wait "$PID"
