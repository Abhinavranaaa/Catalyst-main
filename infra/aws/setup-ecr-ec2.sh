#!/usr/bin/env bash
# Create ECR repos + IAM instance role for the EC2 host (read ECR + write CloudWatch logs).
#
# Usage:
#   export AWS_REGION=ap-south-1
#   export AWS_ACCOUNT_ID=123456789012
#   bash infra/aws/setup-ecr-ec2.sh

set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
INSTANCE_ROLE_NAME="catalyst-ec2-instance"
INSTANCE_PROFILE_NAME="catalyst-ec2-instance"

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

echo "==> Creating ECR repositories"
create_ecr_repo "catalyst-main"
create_ecr_repo "catalyst-embed"

echo "==> Creating EC2 instance role + profile"
cat > /tmp/catalyst-ec2-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

if aws iam get-role --role-name "$INSTANCE_ROLE_NAME" >/dev/null 2>&1; then
  echo "IAM role already exists: $INSTANCE_ROLE_NAME"
else
  aws iam create-role \
    --role-name "$INSTANCE_ROLE_NAME" \
    --assume-role-policy-document file:///tmp/catalyst-ec2-trust.json >/dev/null
  echo "Created IAM role: $INSTANCE_ROLE_NAME"
fi

aws iam attach-role-policy \
  --role-name "$INSTANCE_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly >/dev/null || true

aws iam attach-role-policy \
  --role-name "$INSTANCE_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy >/dev/null || true

# Extra logs policy so docker awslogs driver can create groups/streams
cat > /tmp/catalyst-ec2-logs.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/catalyst/ec2/*",
        "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/catalyst/ec2/*:log-stream:*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name "$INSTANCE_ROLE_NAME" \
  --policy-name catalyst-ec2-cloudwatch-logs \
  --policy-document file:///tmp/catalyst-ec2-logs.json >/dev/null

if aws iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1; then
  echo "Instance profile already exists: $INSTANCE_PROFILE_NAME"
else
  aws iam create-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null
  aws iam add-role-to-instance-profile \
    --instance-profile-name "$INSTANCE_PROFILE_NAME" \
    --role-name "$INSTANCE_ROLE_NAME" >/dev/null
  echo "Created instance profile: $INSTANCE_PROFILE_NAME"
fi

cat <<EOF

Done.

ECR:
  ${ECR_REGISTRY}/catalyst-main
  ${ECR_REGISTRY}/catalyst-embed

Attach instance profile "${INSTANCE_PROFILE_NAME}" to your EC2 instance.

GitHub secrets for CI image push:
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_REGION=${AWS_REGION}
  ECR_REGISTRY=${ECR_REGISTRY}

First image push:
  aws ecr get-login-password --region \$AWS_REGION | docker login --username AWS --password-stdin \$ECR_REGISTRY
  docker build -f servers/catalyst/Dockerfile -t \$ECR_REGISTRY/catalyst-main:latest servers/catalyst
  docker push \$ECR_REGISTRY/catalyst-main:latest
  docker build -f servers/embed/Dockerfile -t \$ECR_REGISTRY/catalyst-embed:latest servers/embed
  docker push \$ECR_REGISTRY/catalyst-embed:latest

GCP Cloud Tasks SA (on the EC2 host):
  1. Create/reuse a SA with roles/cloudtasks.enqueuer (+ roles/iam.serviceAccountUser on the OIDC SA if needed)
  2. Download JSON key → /opt/catalyst/secrets/gcp-sa.json
  3. Set TASKS_SA_EMAIL to the OIDC service account email used in task payloads

EOF
