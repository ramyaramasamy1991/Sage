#!/usr/bin/env bash
# Build the Sage image and push it to Amazon ECR.
#
#   AWS_REGION=us-east-1 AWS_ACCOUNT_ID=123456789012 ./deploy/push-to-ecr.sh
#
set -euo pipefail

: "${AWS_REGION:?set AWS_REGION}"
: "${AWS_ACCOUNT_ID:?set AWS_ACCOUNT_ID}"
REPO="${REPO:-sage}"
TAG="${TAG:-latest}"
REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE="${REGISTRY}/${REPO}:${TAG}"

# Create the repo if it doesn't exist (idempotent).
aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$REPO" --region "$AWS_REGION" >/dev/null

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

docker build -t "$IMAGE" .
docker push "$IMAGE"

echo "Pushed: $IMAGE"
