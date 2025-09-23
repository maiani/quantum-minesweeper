#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/config.sh"

if [ -z "${GCP_PROJECT:-}" ]; then
  echo "Set GCP_PROJECT (in .env or env)" >&2
  exit 1
fi

TAG="${GITHUB_REF_NAME:-$(git describe --tags --always || echo 'manual')}"
REMOTE_IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT}/qms/${IMAGE_NAME}:${TAG}"

echo ">>> Building and pushing $REMOTE_IMAGE"
docker buildx build --platform linux/amd64 -t "$REMOTE_IMAGE" --push .

echo ">>> Deploying to Cloud Run: $SERVICE"
# Cloud Run injects $PORT; we don't pass it.
# Pass app configs (QMS_*) from your CI secrets/vars or .env if desired.
gcloud run deploy "$SERVICE" \
  --image "$REMOTE_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "QMS_ENABLE_AUTH=${QMS_ENABLE_AUTH:-1},QMS_USER=${QMS_USER:-},QMS_PASS=${QMS_PASS:-},QMS_AUTH_TOKEN=${QMS_AUTH_TOKEN:-},QMS_BACKEND=${QMS_BACKEND:-stim},QMS_ENABLE_HELP=${QMS_ENABLE_HELP:-1},QMS_ENABLE_TUTORIAL=${QMS_ENABLE_TUTORIAL:-1},QMS_TUTORIAL_URL=${QMS_TUTORIAL_URL:-},QMS_BASE_URL=${QMS_BASE_URL:-}"
