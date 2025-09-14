#!/usr/bin/env bash
set -euo pipefail

# ---- Config ----
PROJECT_ID="qminesweeper"        # <-- replace with your project id
REGION="europe-west1"
REPO="qms"
SERVICE="quantum-minesweeper"

DEMO_USER="demo"
DEMO_PASS="nordita"

TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:${TAG}"

echo ">>> Building image with BuildKit: $IMAGE"

# Ensure auth for Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" -q

# Use buildx with inline cache for faster rebuilds
docker buildx build \
  --platform linux/amd64 \
  --builder qmsbuilder \
  --cache-from=type=registry,ref="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:cache" \
  --cache-to=type=registry,ref="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/qminesweeper:cache",mode=max \
  -t "$IMAGE" \
  --push .

gcloud run services update quantum-minesweeper \
  --region "$REGION" \
  --set-env-vars "DEMO_USER=$DEMO_USER, DEMO_PASS=$DEMO_PASS" \
  --allow-unauthenticated

echo ">>> Deploying to Cloud Run service: $SERVICE"
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo ">>> Deployment complete!"
echo "Service URL: $URL"
