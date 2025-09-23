#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/config.sh"

TAG="local-$(date +%Y%m%d-%H%M%S)"

echo ">>> Building image: $IMAGE (also tagged qminesweeper:$TAG)"

docker build \
  -t "$IMAGE" \
  -t "qminesweeper:$TAG" \
  .

echo "$IMAGE" > .last_image
echo ">>> Build complete: $IMAGE"
