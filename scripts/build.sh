#!/usr/bin/env bash
set -euo pipefail

TAG="local-$(date +%Y%m%d-%H%M%S)"
IMAGE="qminesweeper:latest"

echo ">>> Building local image: $IMAGE (tagged $TAG too)"

docker build \
  -t "$IMAGE" \
  -t "qminesweeper:$TAG" \
  .

echo "$IMAGE" > .last_image
echo ">>> Build complete: $IMAGE"
