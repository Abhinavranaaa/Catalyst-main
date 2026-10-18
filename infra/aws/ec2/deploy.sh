#!/usr/bin/env bash
# Pull latest images from ECR and restart the stack on this EC2 host.
# Run from /opt/catalyst (where docker-compose.yml and .env live).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

: "${AWS_REGION:?Set AWS_REGION in .env}"
: "${ECR_REGISTRY:?Set ECR_REGISTRY in .env}"

GCP_SA_FILE="${GCP_SA_JSON_HOST:-./secrets/gcp-sa.json}"
if [[ ! -f "$GCP_SA_FILE" ]] || ! grep -q '"private_key"' "$GCP_SA_FILE"; then
  echo "WARNING: $GCP_SA_FILE has no GCP private key." >&2
  echo "The API will serve traffic. Cloud Tasks enqueue stays broken until a real key is installed." >&2
  mkdir -p "$(dirname "$GCP_SA_FILE")"
  if [[ ! -f "$GCP_SA_FILE" ]]; then
    printf '%s\n' '{"type":"service_account"}' > "$GCP_SA_FILE"
  fi
fi

echo "==> ECR login"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "==> Pull + up"
docker compose pull
docker compose up -d --remove-orphans

echo "==> Status"
docker compose ps
curl -fsS "http://127.0.0.1:8080/health" && echo
echo "Deploy complete."
