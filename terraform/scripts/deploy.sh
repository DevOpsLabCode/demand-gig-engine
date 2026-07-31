#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Orchestrates validation, image publication, zero-capacity provisioning, database migration, service scaling, frontend publication, and cache invalidation.
# Execution model: fail fast, validate prerequisites, run each documented phase, and surface errors.

set -Eeuo pipefail

ENVIRONMENT="${1:-dev}"
[[ "$ENVIRONMENT" =~ ^(dev|prod)$ ]] || { echo "Usage: $0 dev|prod" >&2; exit 2; }
for command_name in aws terraform docker jq git; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required" >&2; exit 1; }
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TF="$ROOT/terraform"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
TFVARS="envs/$ENVIRONMENT/terraform.tfvars"

# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws sts get-caller-identity >/dev/null
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$TF" fmt -recursive
BACKEND_FILE="$("$TF/scripts/bootstrap.sh" "$ENVIRONMENT")"
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$TF" init -reconfigure -input=false -backend-config="$BACKEND_FILE"
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$TF" validate

# Create only the encryption key and ECR repositories before image publishing.
terraform -chdir="$TF" apply \
  -auto-approve \
  -input=false \
  -lock-timeout=5m \
  -var-file="$TFVARS" \
  -var="backend_image=public.ecr.aws/docker/library/python:3.12-slim" \
  -target=module.kms \
  -target=module.ecr

REPOSITORIES="$(terraform -chdir="$TF" output -json ecr_repository_urls)"
BACKEND_REPOSITORY="$(jq -r .backend <<<"$REPOSITORIES")"
FRONTEND_REPOSITORY="$(jq -r .frontend <<<"$REPOSITORIES")"
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws ecr get-login-password --region "$REGION" | \
  # Build, tag, publish, or inspect the container artifact required by this deployment phase.
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

TAG="${GITHUB_SHA:-$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
# Build, tag, publish, or inspect the container artifact required by this deployment phase.
docker build -f "$ROOT/Dockerfile.backend" -t "$BACKEND_REPOSITORY:$TAG" "$ROOT"
# Build, tag, publish, or inspect the container artifact required by this deployment phase.
docker push "$BACKEND_REPOSITORY:$TAG"
# Build, tag, publish, or inspect the container artifact required by this deployment phase.
docker build -f "$ROOT/Dockerfile.frontend" -t "$FRONTEND_REPOSITORY:$TAG" "$ROOT"
# Build, tag, publish, or inspect the container artifact required by this deployment phase.
docker push "$FRONTEND_REPOSITORY:$TAG"

COMMON_ARGS=(
  -auto-approve
  -input=false
  -lock-timeout=5m
  -var-file="$TFVARS"
  -var="backend_image=$BACKEND_REPOSITORY:$TAG"
)

# Build all infrastructure with services scaled to zero so migrations run once.
terraform -chdir="$TF" apply \
  "${COMMON_ARGS[@]}" \
  -var="backend_desired_count=0" \
  -var="worker_desired_count=0" \
  -var="allow_zero_capacity=true"

# Optional non-interactive provider credential injection. The JSON file must
# contain only the keys documented in terraform/README.md and must not be committed.
if [[ -n "${PROVIDER_CREDENTIALS_FILE:-}" ]]; then
  [[ -f "$PROVIDER_CREDENTIALS_FILE" ]] || { echo "Provider credentials file not found: $PROVIDER_CREDENTIALS_FILE" >&2; exit 1; }
  jq -e 'type == "object"' "$PROVIDER_CREDENTIALS_FILE" >/dev/null
  PROVIDER_SECRET_ARN="$(terraform -chdir="$TF" output -raw provider_credentials_secret_arn)"
  # Call AWS using the active identity and fail if the requested cloud operation is not authorized.
  aws secretsmanager put-secret-value \
    --secret-id "$PROVIDER_SECRET_ARN" \
    --secret-string "file://$PROVIDER_CREDENTIALS_FILE" >/dev/null
fi

CLUSTER_ARN="$(terraform -chdir="$TF" output -raw ecs_cluster_arn)"
TASK_DEFINITION="$(terraform -chdir="$TF" output -raw migration_task_definition_arn)"
SERVICE_NAME="$(terraform -chdir="$TF" output -raw migration_container_name)"
SECURITY_GROUP="$(terraform -chdir="$TF" output -raw app_security_group_id)"
SUBNETS="$(terraform -chdir="$TF" output -json app_subnet_ids | jq -r 'join(",")')"
OVERRIDES="$(jq -cn --arg name "$SERVICE_NAME" '{containerOverrides:[{name:$name,command:["python","manage.py","migrate","--noinput"]}]}')"

MIGRATION_TASK="$(aws ecs run-task \
  --cluster "$CLUSTER_ARN" \
  --launch-type FARGATE \
  --task-definition "$TASK_DEFINITION" \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --overrides "$OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text)"
[[ "$MIGRATION_TASK" != "None" && -n "$MIGRATION_TASK" ]] || { echo "Failed to start migration task" >&2; exit 1; }
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws ecs wait tasks-stopped --cluster "$CLUSTER_ARN" --tasks "$MIGRATION_TASK"
MIGRATION_EXIT_CODE="$(aws ecs describe-tasks \
  --cluster "$CLUSTER_ARN" \
  --tasks "$MIGRATION_TASK" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"
[[ "$MIGRATION_EXIT_CODE" == "0" ]] || {
  # Call AWS using the active identity and fail if the requested cloud operation is not authorized.
  aws ecs describe-tasks --cluster "$CLUSTER_ARN" --tasks "$MIGRATION_TASK"
  echo "Database migration task failed with exit code $MIGRATION_EXIT_CODE" >&2
  exit 1
}

# Scale the API and worker services to their environment-specific desired counts.
terraform -chdir="$TF" apply "${COMMON_ARGS[@]}"

STATIC_BUCKET="$(terraform -chdir="$TF" output -raw static_bucket_id)"
DISTRIBUTION_ID="$(terraform -chdir="$TF" output -raw cloudfront_distribution_id)"
CONTAINER_ID="$(docker create "$FRONTEND_REPOSITORY:$TAG")"
ASSET_DIR="$(mktemp -d)"
trap 'docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true; rm -rf "$ASSET_DIR"' EXIT

# Build, tag, publish, or inspect the container artifact required by this deployment phase.
docker cp "$CONTAINER_ID:/usr/share/nginx/html/." "$ASSET_DIR/"
# Build, tag, publish, or inspect the container artifact required by this deployment phase.
docker rm "$CONTAINER_ID" >/dev/null
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3 sync "$ASSET_DIR" "s3://$STATIC_BUCKET" \
  --delete \
  --exclude "index.html" \
  --cache-control "public,max-age=31536000,immutable" \
  --only-show-errors
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3 cp "$ASSET_DIR/index.html" "s3://$STATIC_BUCKET/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache,no-store,must-revalidate" \
  --only-show-errors
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths '/*' >/dev/null

# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$TF" output
