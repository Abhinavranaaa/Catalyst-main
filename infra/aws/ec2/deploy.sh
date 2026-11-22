#!/usr/bin/env bash
# Pull latest images from ECR and restart the stack on this EC2 host.
# Run from /opt/catalyst (where docker-compose.yml and .env live).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing compose .env (AWS_REGION, ECR_REGISTRY, IMAGE_TAG) in $ROOT" >&2
  exit 1
fi
if [[ ! -f api.env ]]; then
  echo "Missing api.env in $ROOT" >&2
  exit 1
fi
if [[ ! -f embed.env ]]; then
  echo "Missing embed.env in $ROOT" >&2
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

CADDYFILE_NAME="${CADDYFILE:-Caddyfile.internal}"
if [[ "${CADDYFILE_NAME}" == *internal* ]]; then
  mkdir -p certs
  if [[ ! -f certs/cert.pem || ! -f certs/key.pem ]]; then
    EIP="$(curl -fsS --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 127.0.0.1)"
    echo "==> Generating self-signed TLS cert for ${EIP}"
    openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes \
      -keyout certs/key.pem -out certs/cert.pem \
      -subj "/CN=${EIP}" \
      -addext "subjectAltName=IP:${EIP}"
  fi
fi

echo "==> ECR login"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "==> Pull + up"
# Prefer pulling only what changed; full API image pull is multi‑GB and often times out under SSM.
docker compose pull caddy || true
docker compose up -d --remove-orphans

echo "==> Status"
docker compose ps
curl -fsS "http://127.0.0.1:8080/health" && echo

CADDYFILE_NAME="${CADDYFILE:-Caddyfile.internal}"
EIP="$(curl -fsS --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"

if [[ "${CADDYFILE_NAME}" == *internal* ]]; then
  TARGET="https://127.0.0.1/health"
  [[ -n "${EIP}" ]] && TARGET="https://${EIP}/health"
  if curl -fsSk --connect-timeout 5 "${TARGET}" >/dev/null 2>&1; then
    echo "TLS ok (self-signed): ${TARGET}"
    echo "Insomnia: https://${EIP:-EIP} — turn SSL validation OFF. Cookie jwt binds to this IP until DNS."
  else
    echo "WARNING: HTTPS on :443 not ready. Open SG 443; check: docker compose logs caddy --tail 50" >&2
  fi
else
  HOST="${API_HOSTNAME:-api.catalystedutech.com}"
  if curl -fsSk --connect-timeout 5 "https://${HOST}/health" >/dev/null 2>&1; then
    echo "TLS ok (Let's Encrypt): https://${HOST}/health"
  else
    echo "WARNING: https://${HOST}/health not ready. Need DNS A → EIP + SG 80/443." >&2
  fi
fi
echo "Deploy complete."
