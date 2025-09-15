#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/config.sh"

TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:${TAG}"

echo ">>> Building and pushing image: $IMAGE"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" -q
docker buildx build \
  --platform linux/amd64 \
  -t "$IMAGE" \
  --push .

echo "$IMAGE" > .last_image

echo ">>> Deploying to Cloud Run: $SERVICE with image $IMAGE"
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars QMS_ENABLE_AUTH="${QMS_ENABLE_AUTH:-1}",QMS_USER="$QMS_USER",QMS_PASS="$QMS_PASS"

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo ">>> Deployment complete!"
echo "Service URL: $URL"
