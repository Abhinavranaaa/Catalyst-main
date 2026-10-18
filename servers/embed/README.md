# Embedding service lives in a separate repo:
#   /Users/abhinavrana/catalyst-services  (main.py FastAPI /embed)
#
# Do not put a stub here. Build the ECR image from that repo:
#   docker build -t $ECR_REGISTRY/catalyst-embed:latest /path/to/catalyst-services
#
# Or: bash infra/aws/build-and-push-both.sh
