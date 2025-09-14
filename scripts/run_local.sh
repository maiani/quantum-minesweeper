#!/usr/bin/env bash
set -euo pipefail
IMAGE=$(cat .last_image)

echo ">>> Running locally at http://localhost:8080"
docker run -p 8080:8080 "$IMAGE"
