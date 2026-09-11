#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/config.sh"

if [ -z "${GCP_PROJECT:-}" ]; then
  echo "Set GCP_PROJECT (in .env or env)" >&2
  exit 1
fi

TAG="${IMAGE_TAG:-${GITHUB_REF_NAME:-$(git describe --tags --always || echo 'manual')}}"
REMOTE_IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPO}/${IMAGE_NAME}:${TAG}"

echo ">>> Building and pushing $REMOTE_IMAGE"
# --provenance/--sbom=false: skip the attestation manifests buildx would otherwise
# push as extra untagged versions. They inflate the repo and would consume slots in
# the "keep most recent 3" cleanup policy, so each deploy stays exactly one version.
docker buildx build --platform linux/amd64 --provenance=false --sbom=false -t "$REMOTE_IMAGE" --push .

echo ">>> Deploying to Cloud Run: $SERVICE"
# Cloud Run injects $PORT; we don't pass it.
# Pass app configs (QMS_*) from your CI secrets/vars or .env if desired.
# QMS_BROWSER_DIST_DIR and QMS_BROWSER_ANALYTICS_URL are deliberately absent:
# the image sets them itself when it builds and ships the installable PWA.
ENV_VAR_ITEMS=(
  "QMS_ENABLE_AUTH=${QMS_ENABLE_AUTH:-1}"
  "QMS_USER=${QMS_USER:-}"
  "QMS_PASS=${QMS_PASS:-}"
  "QMS_ADMIN_PASS=${QMS_ADMIN_PASS:-}"
  "QMS_BACKEND=${QMS_BACKEND:-stim}"
  "QMS_ENABLE_HELP=${QMS_ENABLE_HELP:-1}"
  "QMS_ENABLE_ABOUT=${QMS_ENABLE_ABOUT:-1}"
  "QMS_ENABLE_TUTORIAL=${QMS_ENABLE_TUTORIAL:-0}"
  "QMS_TUTORIAL_URL=${QMS_TUTORIAL_URL:-}"
  "QMS_RESET_POLICY=${QMS_RESET_POLICY:-sandbox}"
  "QMS_ENABLE_SURVEY=${QMS_ENABLE_SURVEY:-0}"
  "QMS_SURVEY_URL=${QMS_SURVEY_URL:-}"
  "QMS_ENABLE_ENTANGLEMENT_PROBES=${QMS_ENABLE_ENTANGLEMENT_PROBES:-1}"
  "QMS_BASE_URL=${QMS_BASE_URL:-}"
  "QMS_DB_PATH=${QMS_DB_PATH:-/tmp/qms.sqlite}"
  "QMS_GA_MEASUREMENT_ID=${QMS_GA_MEASUREMENT_ID:-}"
  "QMS_ENABLE_BROWSER_ANALYTICS=${QMS_ENABLE_BROWSER_ANALYTICS:-1}"
  "QMS_ANALYTICS_ALLOWED_ORIGINS=${QMS_ANALYTICS_ALLOWED_ORIGINS:-}"
  "QMS_ANALYTICS_RATE_LIMIT_PER_MINUTE=${QMS_ANALYTICS_RATE_LIMIT_PER_MINUTE:-60}"
  "QMS_ANALYTICS_GLOBAL_LIMIT_PER_MINUTE=${QMS_ANALYTICS_GLOBAL_LIMIT_PER_MINUTE:-600}"
  "QMS_ANALYTICS_MAX_BROWSER_ROWS=${QMS_ANALYTICS_MAX_BROWSER_ROWS:-50000}"
  "QMS_ANALYTICS_RETENTION_DAYS=${QMS_ANALYTICS_RETENTION_DAYS:-365}"
  "QMS_ENABLE_BROWSER_APP=${QMS_ENABLE_BROWSER_APP:-1}"
)
# gcloud accepts a custom delimiter via the ^DELIM^ prefix. A comma cannot be
# the delimiter because ANALYTICS_ALLOWED_ORIGINS is itself comma-separated.
ENV_VARS="$(IFS='|'; echo "^|^${ENV_VAR_ITEMS[*]}")"

DEPLOY_ARGS=(
  gcloud run deploy "$SERVICE"
  --image "$REMOTE_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "$ENV_VARS" \
  --memory="${CLOUD_RUN_MEMORY:-512Mi}" \
  --cpu="${CLOUD_RUN_CPU:-1}" \
  --concurrency="${CLOUD_RUN_CONCURRENCY:-200}" \
  --min-instances="${CLOUD_RUN_MIN_INSTANCES:-0}" \
  --max-instances="${CLOUD_RUN_MAX_INSTANCES:-1}" \
  --timeout="${CLOUD_RUN_TIMEOUT:-300}"
)

if [ -n "${QMS_BUCKET:-}" ]; then
  DEPLOY_ARGS+=(
    --add-volume "name=games-vol,type=cloud-storage,bucket=${QMS_BUCKET}"
    --add-volume-mount "volume=games-vol,mount-path=/data"
  )
fi

"${DEPLOY_ARGS[@]}"
