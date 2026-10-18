#!/usr/bin/env bash
# Build both images locally and push to ECR.
# Expects catalyst-services as a sibling directory (or CATALYST_SERVICES_DIR).
#
# Usage:
#   export AWS_REGION=ap-south-1
#   export AWS_ACCOUNT_ID=123456789012
#   bash infra/aws/build-and-push-both.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SERVICES_DIR="${CATALYST_SERVICES_DIR:-$(cd "$ROOT/../catalyst-services" 2>/dev/null && pwd || true)}"

: "${AWS_REGION:?Set AWS_REGION}"
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"

if [[ -z "${SERVICES_DIR}" || ! -f "${SERVICES_DIR}/main.py" ]]; then
  echo "catalyst-services not found. Set CATALYST_SERVICES_DIR to that repo root." >&2
  echo "Expected main.py embedding API at \$CATALYST_SERVICES_DIR/main.py" >&2
  exit 1
fi

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
TAG="${IMAGE_TAG:-latest}"

echo "==> ECR login ($ECR_REGISTRY)"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "==> Build/push catalyst-main"
docker build \
  -f "$ROOT/servers/catalyst/Dockerfile" \
  -t "$ECR_REGISTRY/catalyst-main:$TAG" \
  "$ROOT/servers/catalyst"
docker push "$ECR_REGISTRY/catalyst-main:$TAG"

echo "==> Build/push catalyst-embed (from $SERVICES_DIR)"
docker build \
  -t "$ECR_REGISTRY/catalyst-embed:$TAG" \
  "$SERVICES_DIR"
docker push "$ECR_REGISTRY/catalyst-embed:$TAG"

echo "Done."
echo "  $ECR_REGISTRY/catalyst-main:$TAG"
echo "  $ECR_REGISTRY/catalyst-embed:$TAG"
