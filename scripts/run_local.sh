#!/usr/bin/env bash
set -euo pipefail

# Load config (defines IMAGE, PORT, CONTAINER_NAME, etc.)
source "$(dirname "$0")/config.sh"

# Use last built image if available, else default IMAGE
if [ -f .last_image ]; then
  IMAGE=$(cat .last_image)
  echo ">>> Using last built image: $IMAGE"
else
  echo ">>> No .last_image found, falling back to default IMAGE: $IMAGE"
fi
# Stop/remove existing container if running
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
  echo ">>> Stopping existing container: $CONTAINER_NAME"
  docker rm -f "$CONTAINER_NAME"
fi

echo ">>> Running $IMAGE locally on port $PORT..."

docker run --name "$CONTAINER_NAME" \
  -p "${PORT}:${PORT}" \
  --env-file .env \
  "$IMAGE"
