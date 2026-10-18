#!/usr/bin/env bash
# One-time bootstrap for AWS deploy targets used by .github/workflows/deploy-aws.yml
#
# Usage:
#   export AWS_REGION=ap-south-1
#   export AWS_ACCOUNT_ID=123456789012
#   bash infra/aws/setup-ecr-apprunner.sh
#
# After this script finishes, copy the printed ARNs into GitHub secrets:
#   ECR_REGISTRY
#   APP_RUNNER_SERVICE_ARN_MAIN
#   APP_RUNNER_SERVICE_ARN_EMBED

set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ACCESS_ROLE_NAME="catalyst-apprunner-ecr-access"
INSTANCE_ROLE_NAME="catalyst-apprunner-instance"

create_ecr_repo() {
  local repo="$1"
  if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "ECR repo already exists: $repo"
  else
    aws ecr create-repository \
      --repository-name "$repo" \
      --image-scanning-configuration scanOnPush=true \
      --region "$AWS_REGION" >/dev/null
    echo "Created ECR repo: $repo"
  fi
}

ensure_trust_policy() {
  local role_name="$1"
  local policy_file="$2"
  if aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
    echo "IAM role already exists: $role_name"
  else
    aws iam create-role \
      --role-name "$role_name" \
      --assume-role-policy-document "file://${policy_file}" >/dev/null
    echo "Created IAM role: $role_name"
  fi
}

attach_managed_policy() {
  local role_name="$1"
  local policy_arn="$2"
  aws iam attach-role-policy \
    --role-name "$role_name" \
    --policy-arn "$policy_arn" >/dev/null || true
}

write_apprunner_access_trust() {
  cat > /tmp/apprunner-access-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "build.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

write_apprunner_instance_trust() {
  cat > /tmp/apprunner-instance-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

create_apprunner_service() {
  local service_name="$1"
  local ecr_repo="$2"
  local cpu="$3"
  local memory="$4"

  if ! aws ecr describe-images \
      --repository-name "$ecr_repo" \
      --image-ids imageTag=latest \
      --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "SKIP: no :latest image in ${ecr_repo} yet — push an image before creating ${service_name}" >&2
    return 0
  fi

  local existing_arn
  existing_arn="$(aws apprunner list-services --region "$AWS_REGION" \
    --query "ServiceSummaryList[?ServiceName=='${service_name}'].ServiceArn | [0]" \
    --output text)"

  if [[ "$existing_arn" != "None" && -n "$existing_arn" ]]; then
    echo "App Runner service already exists: $service_name ($existing_arn)" >&2
    echo "$existing_arn"
    return
  fi

  local access_role_arn
  access_role_arn="$(aws iam get-role --role-name "$ACCESS_ROLE_NAME" --query Role.Arn --output text)"
  local instance_role_arn
  instance_role_arn="$(aws iam get-role --role-name "$INSTANCE_ROLE_NAME" --query Role.Arn --output text)"

  local service_arn
  service_arn="$(aws apprunner create-service \
    --region "$AWS_REGION" \
    --service-name "$service_name" \
    --source-configuration "{
      \"AuthenticationConfiguration\": {
        \"AccessRoleArn\": \"${access_role_arn}\"
      },
      \"AutoDeploymentsEnabled\": false,
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${ECR_REGISTRY}/${ecr_repo}:latest\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"8080\"
        }
      }
    }" \
    --instance-configuration "{
      \"Cpu\": \"${cpu}\",
      \"Memory\": \"${memory}\",
      \"InstanceRoleArn\": \"${instance_role_arn}\"
    }" \
    --health-check-configuration "{
      \"Protocol\": \"HTTP\",
      \"Path\": \"/health\",
      \"Interval\": 10,
      \"Timeout\": 5,
      \"HealthyThreshold\": 1,
      \"UnhealthyThreshold\": 5
    }" \
    --query Service.ServiceArn \
    --output text)"

  echo "Created App Runner service: $service_name ($service_arn)" >&2
  echo "$service_arn"
}

echo "==> Creating ECR repositories"
create_ecr_repo "catalyst-main"
create_ecr_repo "catalyst-embed"

echo "==> Creating App Runner IAM roles"
write_apprunner_access_trust
write_apprunner_instance_trust
ensure_trust_policy "$ACCESS_ROLE_NAME" /tmp/apprunner-access-trust.json
ensure_trust_policy "$INSTANCE_ROLE_NAME" /tmp/apprunner-instance-trust.json
attach_managed_policy "$ACCESS_ROLE_NAME" "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
attach_managed_policy "$INSTANCE_ROLE_NAME" "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"

echo "==> Creating App Runner services (skipped if ECR repos have no :latest image yet)"
MAIN_ARN="$(create_apprunner_service catalyst-main catalyst-main 2048 2048)"
EMBED_ARN="$(create_apprunner_service catalyst-embed catalyst-embed 1024 2048)"

cat <<EOF

Done.

GitHub secrets (required for CI/CD):
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_REGION=${AWS_REGION}
  ECR_REGISTRY=${ECR_REGISTRY}

EOF

if [[ -n "${MAIN_ARN:-}" ]]; then
  echo "  APP_RUNNER_SERVICE_ARN_MAIN=${MAIN_ARN}"
else
  cat <<'EOF'
  APP_RUNNER_SERVICE_ARN_MAIN   (set after first catalyst-main image push + App Runner create)

First image push example:
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
  docker build -f servers/catalyst/Dockerfile -t $ECR_REGISTRY/catalyst-main:latest servers/catalyst
  docker push $ECR_REGISTRY/catalyst-main:latest
  bash infra/aws/setup-ecr-apprunner.sh   # re-run to create the App Runner service
EOF
fi

if [[ -n "${EMBED_ARN:-}" ]]; then
  echo "  APP_RUNNER_SERVICE_ARN_EMBED=${EMBED_ARN}"
else
  cat <<'EOF'
  APP_RUNNER_SERVICE_ARN_EMBED  (set after first catalyst-embed image push + App Runner create)

First image push example:
  docker build -f servers/embed/Dockerfile -t $ECR_REGISTRY/catalyst-embed:latest servers/embed
  docker push $ECR_REGISTRY/catalyst-embed:latest
  bash infra/aws/setup-ecr-apprunner.sh   # re-run to create the App Runner service
EOF
fi

cat <<EOF

After App Runner services exist:
  1. Configure runtime environment variables on catalyst-main (mirror servers/catalyst/.env).
  2. Set EMBED_SERVICE_BASE on catalyst-main to the catalyst-embed App Runner URL.
  3. Point Cloudflare api.catalystedutech.com at the catalyst-main App Runner URL.

EOF
