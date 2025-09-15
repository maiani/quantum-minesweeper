#!/usr/bin/env bash
set -euo pipefail

# Default to using local .env if present
ENV_FILE_OPT=""
if [ -f .env ]; then
  ENV_FILE_OPT="--env-file .env"
fi

IMAGE=$(cat .last_image 2>/dev/null || echo "qminesweeper:latest")

echo ">>> Running $IMAGE locally..."
docker run -p 8080:8080 $ENV_FILE_OPT "$IMAGE"
