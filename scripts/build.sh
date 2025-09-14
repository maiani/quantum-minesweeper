#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/config.sh"

TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:${TAG}"

echo ">>> Building image with BuildKit: $IMAGE"

# Ensure Artifact Registry auth
gcloud auth configure-docker "${REGION}-docker.pkg.dev" -q

# Build once with both local + remote tags
docker buildx build \
  --platform linux/amd64 \
  --builder qmsbuilder \
  --cache-from=type=registry,ref="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:cache" \
  --cache-to=type=registry,ref="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:cache",mode=max \
  -t "$IMAGE" \
  --push .

# Save the last built image tag for later scripts
echo "$IMAGE" > .last_image

echo ">>> Build complete: $IMAGE"
