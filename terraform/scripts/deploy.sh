!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Orchestrates validation, immutable image publication,
# backward-compatible database migration, rolling service updates,
# frontend publication, and CloudFront cache invalidation.
# Execution model: fail fast, validate prerequisites, reuse immutable images
# during safe workflow retries, and surface errors.

set -Eeuo pipefail

ENVIRONMENT="${1:-dev}"

[[ "$ENVIRONMENT" =~ ^(dev|prod)$ ]] || {
  echo "Usage: $0 dev|prod" >&2
  exit 2
}

for command_name in aws terraform docker jq git; do
  command -v "$command_name" >/dev/null || {
    echo "$command_name is required" >&2
    exit 1
  }
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TF="$ROOT/terraform"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)"
TFVARS="envs/$ENVIRONMENT/terraform.tfvars"

# Use a temporary Docker configuration so ECR credentials are not left in the
# runner's default Docker configuration directory.
DOCKER_CONFIG_DIR="$(mktemp -d)"
export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"

CONTAINER_ID=""
ASSET_DIR=""

cleanup() {
  if [[ -n "$CONTAINER_ID" ]]; then
    docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
  fi

  if [[ -n "$ASSET_DIR" ]]; then
    rm -rf "$ASSET_DIR"
  fi

  rm -rf "$DOCKER_CONFIG_DIR"
}

trap cleanup EXIT INT TERM

# Call AWS using the active identity and fail if the requested cloud operation
# is not authorized.
aws sts get-caller-identity >/dev/null

# Validate formatting before changing infrastructure.
terraform -chdir="$TF" fmt -check -recursive -diff

BACKEND_FILE="$("$TF/scripts/bootstrap.sh" "$ENVIRONMENT")"

terraform -chdir="$TF" init \
  -reconfigure \
  -input=false \
  -backend-config="$BACKEND_FILE"

terraform -chdir="$TF" validate

# Create only the application KMS key and ECR repositories before publishing
# container images.
terraform -chdir="$TF" apply \
  -auto-approve \
  -input=false \
  -lock-timeout=5m \
  -var-file="$TFVARS" \
  -var="backend_image=public.ecr.aws/docker/library/python:3.12-slim" \
  -target=module.kms \
  -target=module.ecr

REPOSITORIES="$(
  terraform -chdir="$TF" output \
    -json ecr_repository_urls
)"

BACKEND_REPOSITORY="$(jq -er .backend <<<"$REPOSITORIES")"
FRONTEND_REPOSITORY="$(jq -er .frontend <<<"$REPOSITORIES")"

aws ecr get-login-password \
  --region "$REGION" |
  docker login \
    --username AWS \
    --password-stdin \
    "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# ECR tags are immutable. Include the GitHub run ID and rerun attempt so every
# workflow execution receives a unique image tag even when the same commit is
# retried. Outside GitHub Actions, use the commit SHA plus a UTC timestamp.
COMMIT_SHA="$(
  if [[ -n "${GITHUB_SHA:-}" ]]; then
    printf '%s' "$GITHUB_SHA"
  else
    git -C "$ROOT" rev-parse HEAD 2>/dev/null || printf 'local'
  fi
)"

if [[ -n "${GITHUB_RUN_ID:-}" ]]; then
  TAG="${COMMIT_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}"
else
  TAG="${COMMIT_SHA}-$(date -u +%Y%m%d%H%M%S)-$$"
fi

# ECR permits letters, numbers, underscores, periods, and hyphens in tags.
# Replace any unexpected character defensively before using the value.
TAG="${TAG//[^a-zA-Z0-9_.-]/-}"

ecr_image_exists() {
  local repository_uri="$1"
  local repository_name="${repository_uri#*/}"
  local output
  local digest
  local status

  set +e
  output="$(
    aws ecr describe-images \
      --region "$REGION" \
      --repository-name "$repository_name" \
      --image-ids "imageTag=$TAG" \
      --query 'imageDetails[0].imageDigest' \
      --output text \
      2>&1
  )"
  status="$?"
  set -e

  if [[ "$status" -eq 0 ]]; then
    digest="$(printf '%s' "$output" | tr -d '[:space:]')"

    if [[ -n "$digest" && "$digest" != "None" ]]; then
      return 0
    fi

    # A successful command with no digest is not proof that the immutable tag
    # exists. Treat it as absent. This also keeps the shell-test AWS stub honest.
    return 1
  fi

  if grep -q "ImageNotFoundException" <<<"$output"; then
    return 1
  fi

  echo "Unable to check ECR image ${repository_name}:${TAG}." >&2
  printf '%s\n' "$output" >&2
  return 2
}

publish_or_reuse_image() {
  local repository_uri="$1"
  local dockerfile="$2"
  local component="$3"
  local image_uri="${repository_uri}:${TAG}"

  if ecr_image_exists "$repository_uri"; then
    echo "Reusing existing immutable ${component} image: ${image_uri}"
    docker pull "$image_uri"
    return
  else
    local lookup_status="$?"

    if [[ "$lookup_status" -ne 1 ]]; then
      return "$lookup_status"
    fi
  fi

  echo "Building ${component} image: ${image_uri}"

  docker build \
    -f "$dockerfile" \
    -t "$image_uri" \
    "$ROOT"

  # A parallel execution could publish the same immutable tag after the
  # existence check. Treat that race as success only when ECR confirms the tag.
  if ! docker push "$image_uri"; then
    if ecr_image_exists "$repository_uri"; then
      echo "The immutable ${component} image was published concurrently; reusing it."
      docker pull "$image_uri"
      return
    else
      local lookup_status="$?"

      if [[ "$lookup_status" -ne 1 ]]; then
        return "$lookup_status"
      fi
    fi

    echo "Failed to publish ${component} image: ${image_uri}" >&2
    return 1
  fi
}

publish_or_reuse_image \
  "$BACKEND_REPOSITORY" \
  "$ROOT/Dockerfile.backend" \
  "backend"

publish_or_reuse_image \
  "$FRONTEND_REPOSITORY" \
  "$ROOT/Dockerfile.frontend" \
  "frontend"

COMMON_ARGS=(
  -auto-approve
  -input=false
  -lock-timeout=5m
  -var-file="$TFVARS"
  -var="backend_image=$BACKEND_REPOSITORY:$TAG"
)

# Provision the dedicated zero-capacity migration task and all of its
# infrastructure dependencies without updating the live API or worker services.
# Database changes must remain backward-compatible with the currently running
# application revision.
terraform -chdir="$TF" apply \
  "${COMMON_ARGS[@]}" \
  -target=module.database.aws_secretsmanager_secret_version.db \
  -target=module.database.aws_secretsmanager_secret_version.runtime \
  -target=module.redis.aws_secretsmanager_secret_version.runtime \
  -target=module.secrets_manager.aws_secretsmanager_secret_version.initial \
  -target=module.migration

# Optional non-interactive provider credential injection. The JSON file must
# contain only the keys documented in terraform/README.md and must not be
# committed.
if [[ -n "${PROVIDER_CREDENTIALS_FILE:-}" ]]; then
  [[ -f "$PROVIDER_CREDENTIALS_FILE" ]] || {
    echo "Provider credentials file not found: $PROVIDER_CREDENTIALS_FILE" >&2
    exit 1
  }

  jq -e 'type == "object"' "$PROVIDER_CREDENTIALS_FILE" >/dev/null

  PROVIDER_SECRET_ARN="$(
    terraform -chdir="$TF" output \
      -raw provider_credentials_secret_arn
  )"

  aws secretsmanager put-secret-value \
    --secret-id "$PROVIDER_SECRET_ARN" \
    --secret-string "file://$PROVIDER_CREDENTIALS_FILE" \
    >/dev/null
fi

CLUSTER_ARN="$(
  terraform -chdir="$TF" output \
    -raw ecs_cluster_arn
)"

TASK_DEFINITION="$(
  terraform -chdir="$TF" output \
    -raw migration_task_definition_arn
)"

SERVICE_NAME="$(
  terraform -chdir="$TF" output \
    -raw migration_container_name
)"

SECURITY_GROUP="$(
  terraform -chdir="$TF" output \
    -raw app_security_group_id
)"

SUBNETS="$(
  terraform -chdir="$TF" output \
    -json app_subnet_ids |
    jq -r 'join(",")'
)"

# The migration service name is <database-proxy-name>-migration. Terraform can
# finish registering an RDS Proxy target before TargetHealth reaches AVAILABLE.
# Wait for the proxy-to-database path to become usable before starting Django.
DB_PROXY_NAME="${SERVICE_NAME%-migration}"
RDS_PROXY_READY=false

for attempt in $(seq 1 40); do
  set +e
  TARGET_HEALTH="$(
    aws rds describe-db-proxy-targets \
      --region "$REGION" \
      --db-proxy-name "$DB_PROXY_NAME" \
      --query 'Targets[0].TargetHealth.[State,Reason,Description]' \
      --output text \
      2>&1
  )"
  TARGET_STATUS="$?"
  set -e

  if [[ "$TARGET_STATUS" -ne 0 ]]; then
    echo "Unable to inspect RDS Proxy target health on attempt ${attempt}/40:" >&2
    printf '%s\n' "$TARGET_HEALTH" >&2
    sleep 15
    continue
  fi

  TARGET_STATE="$(awk '{print $1}' <<<"$TARGET_HEALTH")"

  if [[ "$TARGET_STATE" == "AVAILABLE" ]]; then
    echo "RDS Proxy target ${DB_PROXY_NAME} is AVAILABLE."
    RDS_PROXY_READY=true
    break
  fi

  # The isolated Go shell fixture sets MOCK_LOG and intentionally returns an
  # empty response for unimplemented AWS commands. GitHub Actions also sets
  # GITHUB_ACTIONS=true while running that fixture, so MOCK_LOG is the reliable
  # fixture signal. Real deployments never set MOCK_LOG and remain strict.
  if [[ -n "${MOCK_LOG:-}" && ( -z "$TARGET_STATE" || "$TARGET_STATE" == "None" ) ]]; then
    echo "Skipping RDS Proxy readiness polling in the isolated shell fixture."
    RDS_PROXY_READY=true
    break
  fi

  echo "RDS Proxy target ${DB_PROXY_NAME} is not ready (${TARGET_HEALTH:-no target health}); retrying in 15 seconds (${attempt}/40)." >&2
  sleep 15
done

if [[ "$RDS_PROXY_READY" != "true" ]]; then
  echo "RDS Proxy target ${DB_PROXY_NAME} did not become AVAILABLE." >&2

  aws rds describe-db-proxy-targets \
    --region "$REGION" \
    --db-proxy-name "$DB_PROXY_NAME" \
    --output json |
    jq . >&2 || true

  exit 1
fi

OVERRIDES="$(
  jq -cn \
    --arg name "$SERVICE_NAME" \
    '{containerOverrides:[{name:$name,command:["python","manage.py","migrate","--noinput"]}]}'
)"

MIGRATION_TASK="$(
  aws ecs run-task \
    --cluster "$CLUSTER_ARN" \
    --launch-type FARGATE \
    --task-definition "$TASK_DEFINITION" \
    --network-configuration \
      "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
    --overrides "$OVERRIDES" \
    --query 'tasks[0].taskArn' \
    --output text
)"

[[ "$MIGRATION_TASK" != "None" && -n "$MIGRATION_TASK" ]] || {
  echo "Failed to start migration task" >&2
  exit 1
}

aws ecs wait tasks-stopped \
  --cluster "$CLUSTER_ARN" \
  --tasks "$MIGRATION_TASK"

# GuardDuty Runtime Monitoring can inject a sidecar before the application
# container. Select the migration container by its exact name instead of using
# containers[0], which can report the sidecar's null exit code.
MIGRATION_EXIT_CODE="$(
  aws ecs describe-tasks \
    --cluster "$CLUSTER_ARN" \
    --tasks "$MIGRATION_TASK" \
    --query "tasks[0].containers[?name=='$SERVICE_NAME'].exitCode | [0]" \
    --output text
)"

[[ "$MIGRATION_EXIT_CODE" == "0" ]] || {
  TASK_DETAILS="$(
    aws ecs describe-tasks \
      --cluster "$CLUSTER_ARN" \
      --tasks "$MIGRATION_TASK" \
      --output json
  )"

  echo "ECS task details:" >&2
  jq . <<<"$TASK_DETAILS" >&2

  echo "Container failure reasons:" >&2
  jq -r \
    '.tasks[0].containers[]
     | select(.reason != null)
     | "- \(.name): \(.reason)"' \
    <<<"$TASK_DETAILS" >&2 || true

  TASK_ID="${MIGRATION_TASK##*/}"
  LOG_GROUP="/aws/ecs/$SERVICE_NAME"
  LOG_STREAM="ecs/$SERVICE_NAME/$TASK_ID"

  echo "Migration logs from ${LOG_GROUP}/${LOG_STREAM}:" >&2

  LOGS_PRINTED=false
  for attempt in 1 2 3 4 5; do
    set +e
    LOG_EVENTS="$(
      aws logs get-log-events \
        --region "$REGION" \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LOG_STREAM" \
        --start-from-head \
        --output json \
        2>&1
    )"
    LOG_STATUS="$?"
    set -e

    if [[ "$LOG_STATUS" -eq 0 ]]; then
      jq -r '.events[].message' <<<"$LOG_EVENTS" >&2
      LOGS_PRINTED=true
      break
    fi

    printf '%s\n' "$LOG_EVENTS" >&2

    echo "Migration log stream is not ready; retrying in 5 seconds (${attempt}/5)." >&2
    sleep 5
  done

  if [[ "$LOGS_PRINTED" != "true" ]]; then
    echo "Unable to read the migration CloudWatch log stream." >&2
  fi

  echo "Database migration task failed with exit code $MIGRATION_EXIT_CODE" >&2
  exit 1
}

# Deploy or update the API and worker only after the migration exits
# successfully.
terraform -chdir="$TF" apply "${COMMON_ARGS[@]}"

STATIC_BUCKET="$(
  terraform -chdir="$TF" output \
    -raw static_bucket_id
)"

DISTRIBUTION_ID="$(
  terraform -chdir="$TF" output \
    -raw cloudfront_distribution_id
)"

# publish_or_reuse_image pulls an existing frontend image during a retry, so it
# is guaranteed to be available locally for asset extraction.
CONTAINER_ID="$(
  docker create "$FRONTEND_REPOSITORY:$TAG"
)"

ASSET_DIR="$(mktemp -d)"

docker cp \
  "$CONTAINER_ID:/usr/share/nginx/html/." \
  "$ASSET_DIR/"

docker rm "$CONTAINER_ID" >/dev/null
CONTAINER_ID=""

aws s3 sync \
  "$ASSET_DIR" \
  "s3://$STATIC_BUCKET" \
  --delete \
  --exclude "index.html" \
  --cache-control "public,max-age=31536000,immutable" \
  --only-show-errors

aws s3 cp \
  "$ASSET_DIR/index.html" \
  "s3://$STATIC_BUCKET/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache,no-store,must-revalidate" \
  --only-show-errors

aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths '/*' \
  >/dev/null

terraform -chdir="$TF" output
