#!/usr/bin/env bash
set -euo pipefail

# --- Load .env if present ---
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# --- Local runtime ---
PORT="${PORT:-8080}"
CONTAINER_NAME="${CONTAINER_NAME:-qminesweeper-local}"

# --- Project & service (for deploy) ---
REGION="${REGION:-europe-west1}"
REPO="${REPO:-qms}"
SERVICE="${SERVICE:-quantum-minesweeper}"

# --- Image naming ---
IMAGE_NAME="${IMAGE_NAME:-qminesweeper}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

if [ -n "${GCP_PROJECT:-}" ]; then
  REGISTRY_HOST="${REGION}-docker.pkg.dev"
  IMAGE="${REGISTRY_HOST}/${GCP_PROJECT}/${REPO}/${IMAGE_NAME}:${IMAGE_TAG}"
else
  # Local-only build if no GCP project
  IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
fi

