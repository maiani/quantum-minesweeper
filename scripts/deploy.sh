#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/config.sh"

IMAGE=$(cat .last_image)

echo ">>> Deploying to Cloud Run: $SERVICE with image $IMAGE"

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --set-env-vars "DEMO_USER=$DEMO_USER,DEMO_PASS=$DEMO_PASS" \
  --allow-unauthenticated

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo ">>> Deployment complete!"
echo "Service URL: $URL"
