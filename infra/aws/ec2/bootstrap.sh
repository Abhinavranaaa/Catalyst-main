#!/usr/bin/env bash
# One-time EC2 bootstrap: Docker, AWS CLI helpers, CloudWatch log groups readiness.
# Run as root (or via user-data) on Amazon Linux 2023 / Ubuntu 22.04+.
#
# Expected after this:
#   /opt/catalyst/{docker-compose.yml,.env,secrets/gcp-sa.json,deploy.sh}

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
INSTALL_DIR="${INSTALL_DIR:-/opt/catalyst}"

echo "==> Installing Docker"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
  fi
  systemctl enable --now docker
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y docker
  systemctl enable --now docker
else
  echo "Unsupported OS; install Docker manually" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "==> Installing Docker Compose plugin"
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

echo "==> Preparing ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}/secrets"
chmod 700 "${INSTALL_DIR}/secrets"

# Allow awslogs driver (instance role needs logs:CreateLogGroup/Stream/PutLogEvents)
echo "==> Creating CloudWatch log groups (idempotent)"
if command -v aws >/dev/null 2>&1; then
  aws logs create-log-group --log-group-name /catalyst/ec2/api --region "$AWS_REGION" 2>/dev/null || true
  aws logs create-log-group --log-group-name /catalyst/ec2/embed --region "$AWS_REGION" 2>/dev/null || true
else
  echo "aws CLI not found; create log groups from your laptop or install awscli"
fi

cat <<EOF

Bootstrap done.

Next on this host:
  1. Copy docker-compose.yml + deploy.sh into ${INSTALL_DIR}
  2. Copy filled .env to ${INSTALL_DIR}/.env
  3. Copy GCP Cloud Tasks SA JSON to ${INSTALL_DIR}/secrets/gcp-sa.json
  4. Attach an instance IAM role with:
       - AmazonEC2ContainerRegistryReadOnly
       - CloudWatchLogsFullAccess (or tighter logs:* on /catalyst/ec2/*)
  5. Open SG inbound 8080 from Cloudflare only (or 443 if you terminate TLS here)
  6. Run: ${INSTALL_DIR}/deploy.sh

EOF
