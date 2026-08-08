#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Orchestrates validation, retained-resource reconciliation,
# immutable image publication, backward-compatible database migration,
# rolling service updates, frontend publication, and CloudFront invalidation.
# Execution model: fail fast, validate prerequisites, reuse immutable images
# during safe workflow retries, and surface actionable errors.

set -Eeuo pipefail

ENVIRONMENT="${1:-dev}"

[[ "$ENVIRONMENT" =~ ^(dev|prod)$ ]] || {
  echo "Usage: $0 dev|prod" >&2
  exit 2
}

for command_name in aws terraform docker jq git sed grep awk seq head tr date mktemp curl cp; do
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

[[ "$ACCOUNT_ID" =~ ^[0-9]{12}$ ]] || {
  echo "Unable to resolve the active 12-digit AWS account ID." >&2
  exit 1
}

# Use a temporary Docker configuration so ECR credentials are not left in the
# runner's default Docker configuration directory.
DOCKER_CONFIG_DIR="$(mktemp -d)"
export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"

CONTAINER_ID=""
ASSET_DIR=""
BACKUP_OVERRIDE_FILE="$TF/zz_deploy_backup_vault_override.tf"
FINAL_PLAN_FILE=""
PROVIDER_SECRET_SOURCE_FILE=""
PROVIDER_SECRET_NORMALIZED_FILE=""

cleanup() {
  if [[ -n "$CONTAINER_ID" ]]; then
    docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
  fi

  if [[ -n "$ASSET_DIR" ]]; then
    rm -rf "$ASSET_DIR"
  fi

  if [[ -n "$FINAL_PLAN_FILE" ]]; then
    rm -f "$FINAL_PLAN_FILE"
  fi

  if [[ -n "$PROVIDER_SECRET_SOURCE_FILE" ]]; then
    rm -f "$PROVIDER_SECRET_SOURCE_FILE"
  fi

  if [[ -n "$PROVIDER_SECRET_NORMALIZED_FILE" ]]; then
    rm -f "$PROVIDER_SECRET_NORMALIZED_FILE"
  fi

  rm -f "$BACKUP_OVERRIDE_FILE"
  rm -rf "$DOCKER_CONFIG_DIR"
}

trap cleanup EXIT INT TERM

# ECS resolves each configured Secrets Manager JSON key before starting a
# container. Keep this schema complete even when credentials are rotated with a
# partial JSON document. Empty strings intentionally disable unconfigured
# providers, matching the secret's Terraform-created initial value.
PROVIDER_CREDENTIAL_DEFAULTS='{"GOOGLE_OAUTH_CLIENT_ID":"","GOOGLE_OAUTH_CLIENT_SECRET":"","FACEBOOK_OAUTH_CLIENT_ID":"","FACEBOOK_OAUTH_CLIENT_SECRET":"","INSTAGRAM_OAUTH_CLIENT_ID":"","INSTAGRAM_OAUTH_CLIENT_SECRET":"","TIKTOK_OAUTH_CLIENT_KEY":"","TIKTOK_OAUTH_CLIENT_SECRET":"","STRIPE_SECRET_KEY":"","STRIPE_WEBHOOK_SECRET":"","META_APP_ID":"","META_APP_SECRET":"","META_PIXEL_ID":"","META_CONVERSIONS_API_TOKEN":"","VIBESMEET_ACCESS_TOKEN":"","VIBESMEET_WEBHOOK_SECRET":""}'

normalize_provider_credentials() {
  local source_file="$1"
  local destination_file="$2"
  local missing_keys

  jq -e 'type == "object"' "$source_file" >/dev/null || {
    echo "Provider credentials must be a JSON object." >&2
    return 1
  }

  missing_keys="$(
    jq -r \
      --argjson defaults "$PROVIDER_CREDENTIAL_DEFAULTS" \
      '[($defaults | keys[]) as $key
        | select(has($key) | not)
        | $key]
       | join(", ")' \
      "$source_file"
  )"

  jq \
    --argjson defaults "$PROVIDER_CREDENTIAL_DEFAULTS" \
    '$defaults + .' \
    "$source_file" \
    >"$destination_file"

  jq -e \
    --argjson defaults "$PROVIDER_CREDENTIAL_DEFAULTS" \
    'type == "object"
     and (. as $credentials
          | all($defaults | keys[];
                . as $key
                | $credentials[$key]
                | type == "string"))' \
    "$destination_file" \
    >/dev/null || {
      echo "Every required provider credential must be a JSON string." >&2
      return 1
    }

  if [[ -n "$missing_keys" ]]; then
    echo "Adding missing provider credential keys with empty values: ${missing_keys}."
  fi
}

ecs_service_has_completed_deployment() {
  local service_name="$1"
  local service_state="$2"

  jq -e \
    --arg service_name "$service_name" \
    'any(
       .services[]?
       | select(.serviceName == $service_name)
       | .deployments[]?;
       .rolloutState == "COMPLETED"
     )' \
    <<<"$service_state" \
    >/dev/null
}

report_ecs_service_diagnostics() {
  local cluster_arn="$1"
  shift

  local service_state
  local describe_status

  set +e
  service_state="$(
    aws ecs describe-services \
      --region "$REGION" \
      --cluster "$cluster_arn" \
      --services "$@" \
      --output json \
      2>&1
  )"
  describe_status="$?"
  set -e

  echo "ECS service diagnostics:" >&2

  if [[ "$describe_status" -ne 0 ]]; then
    echo "Unable to describe failed ECS services." >&2
    printf '%s\n' "$service_state" >&2
    return 0
  fi

  jq -r '
    .failures[]?
    | "Service lookup failure: "
      + (.arn // "unknown")
      + " - "
      + (.reason // "unknown")
  ' <<<"$service_state" >&2

  jq -r '
    .services[]?
    | "Service: \(.serviceName)",
      "  Status/counts: status=\(.status), desired=\(.desiredCount), running=\(.runningCount), pending=\(.pendingCount)",
      "  Deployments:",
      (.deployments[]?
       | "    - status=\(.status), rolloutState="
         + (.rolloutState // "unknown")
         + ", reason="
         + (.rolloutStateReason // "not provided")),
      "  Recent events:",
      (.events[:10][]?
       | "    - \(.createdAt): \(.message)")
  ' <<<"$service_state" >&2
}

restore_secret_if_scheduled_for_deletion() {
  local secret_name="$1"
  local metadata="$2"
  local deleted_date
  local restore_output
  local restore_status

  deleted_date="$(jq -r '.DeletedDate // empty' <<<"$metadata")"

  if [[ -z "$deleted_date" ]]; then
    printf '%s\n' "$metadata"
    return 0
  fi

  echo "Restoring Secrets Manager secret ${secret_name}; scheduled deletion date was ${deleted_date}." >&2

  set +e
  restore_output="$(
    aws secretsmanager restore-secret \
      --region "$REGION" \
      --secret-id "$secret_name" \
      --output json \
      2>&1
  )"
  restore_status="$?"
  set -e

  if [[ "$restore_status" -ne 0 ]]; then
    # A concurrent workflow may have restored the secret after the original
    # describe call. Re-read it before treating the restore as a hard failure.
    metadata="$(
      aws secretsmanager describe-secret \
        --region "$REGION" \
        --secret-id "$secret_name" \
        --output json \
        2>/dev/null || true
    )"

    if [[ -z "$metadata" ||
          -n "$(jq -r '.DeletedDate // empty' <<<"$metadata" 2>/dev/null)" ]]; then
      echo "Unable to restore Secrets Manager secret ${secret_name}." >&2
      printf '%s\n' "$restore_output" >&2
      return "$restore_status"
    fi

    echo "Secret ${secret_name} was restored concurrently." >&2
  fi

  for attempt in $(seq 1 30); do
    metadata="$(
      aws secretsmanager describe-secret \
        --region "$REGION" \
        --secret-id "$secret_name" \
        --output json
    )"

    deleted_date="$(jq -r '.DeletedDate // empty' <<<"$metadata")"

    if [[ -z "$deleted_date" ]]; then
      echo "Verified Secrets Manager deletion was cancelled for ${secret_name}." >&2
      printf '%s\n' "$metadata"
      return 0
    fi

    if [[ "$attempt" -eq 30 ]]; then
      echo "Secret ${secret_name} is still marked for deletion after restore." >&2
      return 1
    fi

    echo "Waiting for ${secret_name} to leave scheduled-deletion state (${attempt}/30)." >&2
    sleep 2
  done
}

recover_secret_kms_keys_preflight() {
  # The Go orchestration fixture sets MOCK_LOG and does not emulate AWS
  # Secrets Manager restoration or KMS recovery.
  if [[ -n "${MOCK_LOG:-}" ]]; then
    return 0
  fi

  local project_name
  local configured_environment
  local secret_prefix
  local secret_name
  local metadata
  local describe_status
  local kms_key_id
  local key_state

  project_name="$(
    sed -nE \
      's/^[[:space:]]*project_name[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
      "$TF/$TFVARS" |
      head -n 1
  )"

  configured_environment="$(
    sed -nE \
      's/^[[:space:]]*environment[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
      "$TF/$TFVARS" |
      head -n 1
  )"

  project_name="${project_name:-demand-gig-engine}"
  configured_environment="${configured_environment:-$ENVIRONMENT}"
  secret_prefix="${project_name}-${configured_environment}"

  for secret_name in \
    "${secret_prefix}/database" \
    "${secret_prefix}/runtime" \
    "${secret_prefix}/redis" \
    "${secret_prefix}/provider-credentials"; do

    set +e
    metadata="$(
      aws secretsmanager describe-secret \
        --region "$REGION" \
        --secret-id "$secret_name" \
        --output json \
        2>&1
    )"
    describe_status="$?"
    set -e

    if [[ "$describe_status" -ne 0 ]]; then
      if grep -Eqi \
        'ResourceNotFoundException|not found|does not exist' \
        <<<"$metadata"; then
        echo "Secret ${secret_name} does not exist; Terraform may create it."
        continue
      fi

      echo "Unable to inspect secret ${secret_name} before Terraform starts." >&2
      printf '%s\n' "$metadata" >&2
      return "$describe_status"
    fi

    # Secret deletion and KMS key deletion are separate AWS state machines.
    # Restore the secret first; GetSecretValue remains blocked while DeletedDate
    # is present even when the encryption key has already been recovered.
    metadata="$(
      restore_secret_if_scheduled_for_deletion \
        "$secret_name" \
        "$metadata"
    )"

    kms_key_id="$(jq -r '.KmsKeyId // empty' <<<"$metadata")"

    if [[ -z "$kms_key_id" ||
          "$kms_key_id" == "alias/aws/secretsmanager" ]]; then
      echo "Secret ${secret_name} uses the AWS-managed Secrets Manager key."
    else
      key_state="$(
        aws kms describe-key \
          --region "$REGION" \
          --key-id "$kms_key_id" \
          --query 'KeyMetadata.KeyState' \
          --output text
      )"

      if [[ "$key_state" == "PendingDeletion" ]]; then
        echo "Cancelling scheduled deletion for KMS key ${kms_key_id} used by ${secret_name}."

        aws kms cancel-key-deletion \
          --region "$REGION" \
          --key-id "$kms_key_id" \
          >/dev/null
      fi

      for attempt in $(seq 1 30); do
        key_state="$(
          aws kms describe-key \
            --region "$REGION" \
            --key-id "$kms_key_id" \
            --query 'KeyMetadata.KeyState' \
            --output text
        )"

        case "$key_state" in
          Enabled)
            break
            ;;
          Disabled)
            echo "Enabling KMS key ${kms_key_id} used by ${secret_name}."

            aws kms enable-key \
              --region "$REGION" \
              --key-id "$kms_key_id" \
              >/dev/null
            ;;
          PendingDeletion|Creating|Updating)
            ;;
          *)
            echo "KMS key ${kms_key_id} is in unsupported state ${key_state}." >&2
            return 1
            ;;
        esac

        if [[ "$attempt" -eq 30 ]]; then
          echo "KMS key ${kms_key_id} did not become Enabled." >&2
          return 1
        fi

        sleep 5
      done
    fi

    # Verify availability without printing the secret value.
    aws secretsmanager get-secret-value \
      --region "$REGION" \
      --secret-id "$secret_name" \
      --query 'VersionId' \
      --output text \
      >/dev/null

    echo "Verified Secrets Manager can decrypt ${secret_name}."
  done
}

aws sts get-caller-identity >/dev/null
recover_secret_kms_keys_preflight

# Validate formatting before changing infrastructure.
terraform -chdir="$TF" fmt -check -recursive -diff

BACKEND_FILE="$("$TF/scripts/bootstrap.sh" "$ENVIRONMENT")"

terraform -chdir="$TF" init \
  -reconfigure \
  -input=false \
  -backend-config="$BACKEND_FILE"

terraform -chdir="$TF" validate

IMPORT_ARGS=(
  -input=false
  -lock-timeout=5m
  -var-file="$TFVARS"
  -var="backend_image=public.ecr.aws/docker/library/python:3.12-slim"
)

terraform_resource_in_state() {
  local address="$1"

  terraform -chdir="$TF" state show "$address" >/dev/null 2>&1
}

terraform_resource_id() {
  local address="$1"

  terraform -chdir="$TF" show -json |
    jq -er \
      --arg address "$address" '
        def modules:
          ., (.child_modules[]? | modules);

        .values.root_module
        | modules
        | .resources[]?
        | select(.address == $address)
        | (.values.key_id // .values.id)
        | select(. != null)
        | tostring
      ' |
    head -n 1
}

read_tfvar_string() {
  local variable_name="$1"
  local fallback="$2"
  local value

  value="$(
    sed -nE \
      "s/^[[:space:]]*${variable_name}[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\\1/p" \
      "$TF/$TFVARS" |
      head -n 1
  )"

  printf '%s\n' "${value:-$fallback}"
}

ensure_kms_key_enabled() {
  local key_id="$1"
  local key_state
  local cancel_requested=false

  for attempt in $(seq 1 30); do
    key_state="$(
      aws kms describe-key \
        --region "$REGION" \
        --key-id "$key_id" \
        --query 'KeyMetadata.KeyState' \
        --output text
    )"

    case "$key_state" in
      Enabled)
        return 0
        ;;
      PendingDeletion)
        if [[ "$cancel_requested" != "true" ]]; then
          echo "Cancelling scheduled deletion for preserved KMS key ${key_id}."

          aws kms cancel-key-deletion \
            --region "$REGION" \
            --key-id "$key_id" \
            >/dev/null

          cancel_requested=true
        fi
        ;;
      Disabled)
        echo "Enabling preserved KMS key ${key_id}."

        aws kms enable-key \
          --region "$REGION" \
          --key-id "$key_id" \
          >/dev/null
        ;;
      Creating|Updating)
        ;;
      *)
        echo "KMS key ${key_id} is in unsupported state ${key_state}." >&2
        return 1
        ;;
    esac

    if [[ "$attempt" -eq 30 ]]; then
      echo "KMS key ${key_id} did not become Enabled." >&2
      return 1
    fi

    echo "Waiting for KMS key ${key_id} to become Enabled (${attempt}/30)."
    sleep 5
  done
}

configure_existing_backup_vault_override() {
  # The Go orchestration fixture does not emulate AWS Backup discovery.
  if [[ -n "${MOCK_LOG:-}" ]]; then
    rm -f "$BACKUP_OVERRIDE_FILE"
    return 0
  fi

  local project_name
  local configured_environment
  local vault_name
  local describe_output
  local describe_status
  local vault_kms_key_arn

  project_name="$(read_tfvar_string project_name demand-gig-engine)"
  configured_environment="$(read_tfvar_string environment "$ENVIRONMENT")"
  vault_name="${project_name}-${configured_environment}"

  set +e
  describe_output="$(
    aws backup describe-backup-vault \
      --region "$REGION" \
      --backup-vault-name "$vault_name" \
      --output json \
      2>&1
  )"
  describe_status="$?"
  set -e

  if [[ "$describe_status" -ne 0 ]]; then
    rm -f "$BACKUP_OVERRIDE_FILE"

    if grep -Eqi \
      'ResourceNotFoundException|not found|does not exist' \
      <<<"$describe_output"; then
      echo "AWS Backup vault ${vault_name} does not exist; current KMS configuration will be used."
      return 0
    fi

    echo "Unable to inspect AWS Backup vault ${vault_name} before Terraform planning." >&2
    printf '%s\n' "$describe_output" >&2
    return "$describe_status"
  fi

  vault_kms_key_arn="$(
    jq -er '.EncryptionKeyArn' \
      <<<"$describe_output"
  )"

  ensure_kms_key_enabled "$vault_kms_key_arn"

  # Terraform override files are merged with the existing root module block.
  # Supplying the vault's real immutable key makes configuration match AWS and
  # prevents a forced replacement of a vault containing recovery points.
  cat > "$BACKUP_OVERRIDE_FILE" <<EOF
# Generated temporarily by terraform/scripts/deploy.sh.
# Do not commit this file.
module "backup" {
  kms_key_arn = "${vault_kms_key_arn}"
}
EOF

  terraform -chdir="$TF" fmt \
    "$(basename "$BACKUP_OVERRIDE_FILE")" \
    >/dev/null

  echo "Configured temporary Backup override with retained key ${vault_kms_key_arn}."
}

reconcile_preserved_kms_alias() {
  # The isolated Go shell fixture does not emulate KMS discovery or Terraform
  # imports. Real GitHub deployments do not set MOCK_LOG.
  if [[ -n "${MOCK_LOG:-}" ]]; then
    return 0
  fi

  local project_name
  local configured_environment
  local resource_name
  local alias_name
  local aliases_json
  local alias_json
  local alias_lookup_status
  local alias_target_key_id
  local state_key_id=""

  project_name="$(read_tfvar_string project_name demand-gig-engine)"
  configured_environment="$(read_tfvar_string environment "$ENVIRONMENT")"
  resource_name="${project_name}-${configured_environment}"
  alias_name="alias/${resource_name}"

  aliases_json="$(
    aws kms list-aliases \
      --region "$REGION" \
      --output json
  )"

  set +e
  alias_json="$(
    jq -cer \
      --arg alias_name "$alias_name" \
      '.Aliases[]? | select(.AliasName == $alias_name)' \
      <<<"$aliases_json" |
      head -n 1
  )"
  alias_lookup_status="$?"
  set -e

  if [[ "$alias_lookup_status" -ne 0 || -z "$alias_json" ]]; then
    echo "KMS alias ${alias_name} does not exist; Terraform will create it."
    return 0
  fi

  alias_target_key_id="$(jq -er '.TargetKeyId' <<<"$alias_json")"

  echo "Found existing KMS alias ${alias_name} targeting ${alias_target_key_id}."

  if terraform_resource_in_state "module.kms.aws_kms_key.this"; then
    state_key_id="$(
      terraform_resource_id "module.kms.aws_kms_key.this"
    )"

    if [[ "$state_key_id" != "$alias_target_key_id" ]]; then
      echo "::warning::Terraform tracks KMS key ${state_key_id}, while ${alias_name} targets retained key ${alias_target_key_id}."
      echo "::warning::Terraform will reconcile the alias. Do not delete the retained key while S3 objects or Backup recovery points still use it."
    fi
  else
    # Reuse the retained key behind the alias so retained S3 and AWS Backup
    # data remain decryptable.
    ensure_kms_key_enabled "$alias_target_key_id"

    echo "Importing preserved KMS key ${alias_target_key_id}."

    terraform -chdir="$TF" import \
      "${IMPORT_ARGS[@]}" \
      "module.kms.aws_kms_key.this" \
      "$alias_target_key_id"
  fi

  if ! terraform_resource_in_state "module.kms.aws_kms_alias.this"; then
    echo "Importing existing KMS alias ${alias_name}."

    terraform -chdir="$TF" import \
      "${IMPORT_ARGS[@]}" \
      "module.kms.aws_kms_alias.this" \
      "$alias_name"
  fi
}

reconcile_existing_s3_bucket() {
  local address="$1"
  local bucket_name="$2"
  local head_output
  local head_status
  local import_output
  local import_status

  if terraform_resource_in_state "$address"; then
    echo "${address} is already present in Terraform state."
    return 0
  fi

  set +e
  head_output="$(
    aws s3api head-bucket \
      --bucket "$bucket_name" \
      --expected-bucket-owner "$ACCOUNT_ID" \
      2>&1
  )"
  head_status="$?"
  set -e

  if [[ "$head_status" -eq 0 ]]; then
    echo "Importing existing account-owned S3 bucket ${bucket_name} into ${address}."

    set +e
    import_output="$(
      terraform -chdir="$TF" import \
        "${IMPORT_ARGS[@]}" \
        "$address" \
        "$bucket_name" \
        2>&1
    )"
    import_status="$?"
    set -e

    if [[ "$import_status" -eq 0 ]]; then
      printf '%s\n' "$import_output"

      if ! terraform_resource_in_state "$address"; then
        echo "Terraform import returned success, but ${address} is still missing from state." >&2
        return 1
      fi

      echo "Verified ${address} is managed in Terraform state."
      return 0
    fi

    # A concurrent deployment may have imported the same address while this
    # process waited for the remote-state lock.
    if terraform_resource_in_state "$address"; then
      echo "S3 bucket ${bucket_name} was imported concurrently; creation is skipped."
      return 0
    fi

    printf '%s\n' "$import_output" >&2
    echo "Failed to import existing S3 bucket ${bucket_name} into ${address}." >&2
    return "$import_status"
  fi

  if grep -Eqi \
    '(^|[^0-9])404([^0-9]|$)|Not Found|NoSuchBucket' \
    <<<"$head_output"; then
    echo "S3 bucket ${bucket_name} does not exist; Terraform will create it."
    return 0
  fi

  echo "Unable to reconcile S3 bucket ${bucket_name} safely." >&2
  echo "The bucket may belong to another AWS account, or the deployment role may lack access." >&2
  printf '%s\n' "$head_output" >&2
  return 1
}

reconcile_existing_s3_buckets() {
  # The Go deployment fixture sets MOCK_LOG and does not emulate S3 discovery
  # or Terraform imports. Real deployments do not set MOCK_LOG.
  if [[ -n "${MOCK_LOG:-}" ]]; then
    return 0
  fi

  local project_name
  local configured_environment
  local resource_prefix

  project_name="$(read_tfvar_string project_name demand-gig-engine)"
  configured_environment="$(read_tfvar_string environment "$ENVIRONMENT")"
  resource_prefix="${project_name}-${configured_environment}-${ACCOUNT_ID}"

  reconcile_existing_s3_bucket \
    "module.access_logs.aws_s3_bucket.this" \
    "${resource_prefix}-access-logs"

  reconcile_existing_s3_bucket \
    "module.static.aws_s3_bucket.this" \
    "${resource_prefix}-static"

  reconcile_existing_s3_bucket \
    "module.media.aws_s3_bucket.this" \
    "${resource_prefix}-media"

  reconcile_existing_s3_bucket \
    "module.cloudtrail.aws_s3_bucket.logs" \
    "${resource_prefix}-cloudtrail"
}

reconcile_existing_backup_vault() {
  # The Go orchestration fixture sets MOCK_LOG and does not emulate AWS Backup
  # discovery, KMS recovery, or Terraform imports.
  if [[ -n "${MOCK_LOG:-}" ]]; then
    return 0
  fi

  local address="module.backup.aws_backup_vault.this"
  local project_name
  local configured_environment
  local vault_name
  local describe_output
  local describe_status
  local vault_kms_key_arn
  local import_output
  local import_status

  project_name="$(read_tfvar_string project_name demand-gig-engine)"
  configured_environment="$(read_tfvar_string environment "$ENVIRONMENT")"
  vault_name="${project_name}-${configured_environment}"

  set +e
  describe_output="$(
    aws backup describe-backup-vault \
      --region "$REGION" \
      --backup-vault-name "$vault_name" \
      --output json \
      2>&1
  )"
  describe_status="$?"
  set -e

  if [[ "$describe_status" -eq 0 ]]; then
    # A Backup vault's KMS key is immutable. Keep the historical key enabled so
    # existing recovery points remain decryptable after a tolerant teardown.
    vault_kms_key_arn="$(
      jq -r '.EncryptionKeyArn // empty' \
        <<<"$describe_output"
    )"

    if [[ -n "$vault_kms_key_arn" ]]; then
      echo "Ensuring retained Backup vault KMS key ${vault_kms_key_arn} is enabled."
      ensure_kms_key_enabled "$vault_kms_key_arn"
    fi

    if terraform_resource_in_state "$address"; then
      echo "${address} is already present in Terraform state; creation is skipped."
      return 0
    fi

    echo "Existing AWS Backup vault found: ${vault_name}."
    echo "Importing it into ${address} so Terraform skips creation."

    set +e
    import_output="$(
      terraform -chdir="$TF" import \
        "${IMPORT_ARGS[@]}" \
        "$address" \
        "$vault_name" \
        2>&1
    )"
    import_status="$?"
    set -e

    if [[ "$import_status" -eq 0 ]]; then
      printf '%s\n' "$import_output"

      if ! terraform_resource_in_state "$address"; then
        echo "Terraform import returned success, but ${address} is still missing from state." >&2
        return 1
      fi

      echo "Verified ${address} is managed in Terraform state; creation is skipped."
      return 0
    fi

    if terraform_resource_in_state "$address"; then
      echo "AWS Backup vault ${vault_name} was imported concurrently; creation is skipped."
      return 0
    fi

    printf '%s\n' "$import_output" >&2
    echo "Failed to import existing AWS Backup vault ${vault_name} into ${address}." >&2
    return "$import_status"
  fi

  if grep -Eqi \
    'ResourceNotFoundException|not found|does not exist' \
    <<<"$describe_output"; then
    echo "AWS Backup vault ${vault_name} does not exist; Terraform will create it."
    return 0
  fi

  echo "Unable to reconcile AWS Backup vault ${vault_name} safely." >&2
  echo "The deployment role may lack backup:DescribeBackupVault, or AWS returned an unexpected error." >&2
  printf '%s\n' "$describe_output" >&2
  return 1
}

reconcile_existing_retained_resources() {
  echo "Reconciling retained S3 buckets and AWS Backup vault."

  reconcile_existing_s3_buckets
  reconcile_existing_backup_vault

  echo "Retained-resource reconciliation completed."
}

# Match the root Backup module to the immutable key of an existing retained
# vault before any Terraform import or apply operation.
configure_existing_backup_vault_override

# Reconcile the retained KMS dependency before importing retained encrypted S3
# buckets and the Backup vault.
reconcile_preserved_kms_alias
reconcile_existing_retained_resources

# Create or reconcile the application KMS resources and ECR repositories before
# publishing immutable application images.
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
  local lookup_status

  if ecr_image_exists "$repository_uri"; then
    echo "Reusing existing immutable ${component} image: ${image_uri}"
    docker pull "$image_uri"
    return 0
  else
    lookup_status="$?"

    if [[ "$lookup_status" -ne 1 ]]; then
      return "$lookup_status"
    fi
  fi

  echo "Building ${component} image: ${image_uri}"

  docker build \
    -f "$dockerfile" \
    -t "$image_uri" \
    "$ROOT"

  if ! docker push "$image_uri"; then
    if ecr_image_exists "$repository_uri"; then
      echo "The immutable ${component} image was published concurrently; reusing it."
      docker pull "$image_uri"
      return 0
    else
      lookup_status="$?"

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

find_secret_metadata() {
  local secret_name="$1"

  aws secretsmanager list-secrets \
    --region "$REGION" \
    --include-planned-deletion \
    --filters "Key=name,Values=$secret_name" \
    --output json |
    jq -cer \
      --arg name "$secret_name" \
      '.SecretList[]? | select(.Name == $name)' |
    head -n 1
}

restore_and_import_secret() {
  local resource_address="$1"
  local secret_name="$2"
  local version_resource_address="${3:-}"
  local metadata
  local lookup_status
  local secret_arn
  local deleted_date
  local version_id

  set +e
  metadata="$(find_secret_metadata "$secret_name" 2>&1)"
  lookup_status="$?"
  set -e

  if [[ "$lookup_status" -ne 0 || -z "$metadata" ]]; then
    if grep -qE 'AccessDenied|UnauthorizedOperation' <<<"$metadata"; then
      echo "Unable to inspect scheduled Secrets Manager secrets." >&2
      printf '%s\n' "$metadata" >&2
      return 1
    fi

    echo "Secret ${secret_name} does not exist; Terraform will create it."
    return 0
  fi

  secret_arn="$(jq -er '.ARN' <<<"$metadata")"
  deleted_date="$(jq -r '.DeletedDate // empty' <<<"$metadata")"

  if [[ -n "$deleted_date" ]]; then
    echo "Restoring scheduled secret ${secret_name}."

    aws secretsmanager restore-secret \
      --region "$REGION" \
      --secret-id "$secret_arn" \
      >/dev/null

    for attempt in $(seq 1 30); do
      metadata="$(find_secret_metadata "$secret_name")"
      deleted_date="$(jq -r '.DeletedDate // empty' <<<"$metadata")"

      if [[ -z "$deleted_date" ]]; then
        echo "Secret ${secret_name} is restored."
        break
      fi

      if [[ "$attempt" -eq 30 ]]; then
        echo "Secret ${secret_name} remained scheduled for deletion." >&2
        return 1
      fi

      echo "Waiting for ${secret_name} restoration (${attempt}/30)."
      sleep 2
    done
  fi

  if ! terraform_resource_in_state "$resource_address"; then
    echo "Importing ${secret_name} into ${resource_address}."

    terraform -chdir="$TF" import \
      "${IMPORT_ARGS[@]}" \
      "$resource_address" \
      "$secret_arn"
  else
    echo "${resource_address} is already present in Terraform state."
  fi

  # Provider credentials may contain manually populated OAuth and payment
  # values. Import the existing AWSCURRENT version so Terraform does not replace
  # those values with the module's initial blank object.
  if [[ -n "$version_resource_address" ]] &&
     ! terraform_resource_in_state "$version_resource_address"; then
    metadata="$(
      aws secretsmanager describe-secret \
        --region "$REGION" \
        --secret-id "$secret_arn" \
        --output json
    )"

    version_id="$(
      jq -r '
        .VersionIdsToStages
        | to_entries[]
        | select(.value | index("AWSCURRENT"))
        | .key
      ' <<<"$metadata" |
        head -n 1
    )"

    if [[ -n "$version_id" && "$version_id" != "null" ]]; then
      echo "Importing the existing AWSCURRENT version for ${secret_name}."

      terraform -chdir="$TF" import \
        "${IMPORT_ARGS[@]}" \
        "$version_resource_address" \
        "${secret_arn}|${version_id}"
    else
      echo "No AWSCURRENT version exists for ${secret_name}; Terraform will create one."
    fi
  fi
}

reconcile_scheduled_secrets() {
  # The Go shell fixture intentionally does not emulate Secrets Manager
  # restoration or Terraform imports.
  if [[ -n "${MOCK_LOG:-}" ]]; then
    return 0
  fi

  local project_name
  local secret_prefix

  project_name="$(read_tfvar_string project_name demand-gig-engine)"
  secret_prefix="${project_name}-${ENVIRONMENT}"

  restore_and_import_secret \
    "module.database.aws_secretsmanager_secret.db" \
    "${secret_prefix}/database"

  restore_and_import_secret \
    "module.database.aws_secretsmanager_secret.runtime" \
    "${secret_prefix}/runtime"

  restore_and_import_secret \
    "module.redis.aws_secretsmanager_secret.runtime" \
    "${secret_prefix}/redis"

  restore_and_import_secret \
    "module.secrets_manager.aws_secretsmanager_secret.social" \
    "${secret_prefix}/provider-credentials" \
    "module.secrets_manager.aws_secretsmanager_secret_version.initial"
}

# Development destroy can schedule Secrets Manager deletion. AWS reserves those
# names during the recovery window, so restore and import them before apply.
reconcile_scheduled_secrets

# Provision the dedicated zero-capacity migration task and its infrastructure
# dependencies without updating the live API or worker services.
terraform -chdir="$TF" apply \
  "${COMMON_ARGS[@]}" \
  -target=module.database.aws_secretsmanager_secret_version.db \
  -target=module.database.aws_secretsmanager_secret_version.runtime \
  -target=module.database.aws_db_proxy_target.this \
  -target=module.redis.aws_secretsmanager_secret_version.runtime \
  -target=module.secrets_manager.aws_secretsmanager_secret_version.initial \
  -target=module.migration

# Normalize the provider secret before ECS resolves its required JSON keys. An
# optional file can replace the current document non-interactively; otherwise
# the current document is repaired in place without exposing credential values.
PROVIDER_SECRET_ARN="$(
  terraform -chdir="$TF" output \
    -raw provider_credentials_secret_arn
)"

PROVIDER_SECRET_SOURCE_FILE="$(mktemp)"
PROVIDER_SECRET_NORMALIZED_FILE="$(mktemp)"
chmod 600 "$PROVIDER_SECRET_SOURCE_FILE" "$PROVIDER_SECRET_NORMALIZED_FILE"

if [[ -n "${PROVIDER_CREDENTIALS_FILE:-}" ]]; then
  [[ -f "$PROVIDER_CREDENTIALS_FILE" ]] || {
    echo "Provider credentials file not found: $PROVIDER_CREDENTIALS_FILE" >&2
    exit 1
  }

  cp "$PROVIDER_CREDENTIALS_FILE" "$PROVIDER_SECRET_SOURCE_FILE"
else
  aws secretsmanager get-secret-value \
    --region "$REGION" \
    --secret-id "$PROVIDER_SECRET_ARN" \
    --query SecretString \
    --output text \
    >"$PROVIDER_SECRET_SOURCE_FILE"
fi

normalize_provider_credentials \
  "$PROVIDER_SECRET_SOURCE_FILE" \
  "$PROVIDER_SECRET_NORMALIZED_FILE"

if [[ -n "${PROVIDER_CREDENTIALS_FILE:-}" ]] ||
   ! jq -s -e '.[0] == .[1]' \
     "$PROVIDER_SECRET_SOURCE_FILE" \
     "$PROVIDER_SECRET_NORMALIZED_FILE" \
     >/dev/null; then
  aws secretsmanager put-secret-value \
    --region "$REGION" \
    --secret-id "$PROVIDER_SECRET_ARN" \
    --secret-string "file://$PROVIDER_SECRET_NORMALIZED_FILE" \
    >/dev/null
else
  echo "Provider credential secret already contains every required JSON key."
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

# Terraform can finish registering an RDS Proxy target before its target health
# reaches AVAILABLE. Wait for the proxy-to-database path before starting Django.
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

  # The isolated Go fixture returns an empty value for unimplemented AWS calls.
  if [[ -n "${MOCK_LOG:-}" &&
        ( -z "$TARGET_STATE" || "$TARGET_STATE" == "None" ) ]]; then
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

# Keep this compact literal because the Go contract test requires the exact
# migration gate fragment: "migrate","--noinput".
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

TASK_DETAILS="$(
  aws ecs describe-tasks \
    --cluster "$CLUSTER_ARN" \
    --tasks "$MIGRATION_TASK" \
    --output json
)"

# GuardDuty Runtime Monitoring can inject a sidecar before the application
# container, so select the migration container by exact name.
MIGRATION_EXIT_CODE="$(
  jq -r \
    --arg container_name "$SERVICE_NAME" \
    '.tasks[0].containers[]?
     | select(.name == $container_name)
     | .exitCode // empty' \
    <<<"$TASK_DETAILS" |
    head -n 1
)"

[[ "$MIGRATION_EXIT_CODE" != "None" ]] || MIGRATION_EXIT_CODE=""

[[ "$MIGRATION_EXIT_CODE" == "0" ]] || {
  echo "ECS task details:" >&2
  jq . <<<"$TASK_DETAILS" >&2

  TASK_STOP_CODE="$(jq -r '.tasks[0].stopCode // empty' <<<"$TASK_DETAILS")"
  TASK_STOP_REASON="$(jq -r '.tasks[0].stoppedReason // empty' <<<"$TASK_DETAILS")"

  [[ -z "$TASK_STOP_CODE" ]] || echo "ECS stop code: $TASK_STOP_CODE" >&2
  [[ -z "$TASK_STOP_REASON" ]] || echo "ECS stopped reason: $TASK_STOP_REASON" >&2

  echo "Container failure reasons:" >&2
  jq -r \
    '.tasks[0].containers[]?
     | select(.reason != null)
     | "- \(.name): \(.reason)"' \
    <<<"$TASK_DETAILS" >&2 || true

  if [[ -z "$MIGRATION_EXIT_CODE" ]]; then
    echo "Database migration container never started; CloudWatch logs are unavailable." >&2
    exit 1
  fi

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

API_SERVICE_NAME="${SERVICE_NAME%-migration}-api"
WORKER_SERVICE_NAME="${SERVICE_NAME%-migration}-worker"

ECS_SERVICE_STATE="$(
  aws ecs describe-services \
    --region "$REGION" \
    --cluster "$CLUSTER_ARN" \
    --services "$API_SERVICE_NAME" "$WORKER_SERVICE_NAME" \
    --output json
)"

BACKEND_ROLLBACK_ENABLED=false
WORKER_ROLLBACK_ENABLED=false

if ecs_service_has_completed_deployment "$API_SERVICE_NAME" "$ECS_SERVICE_STATE"; then
  BACKEND_ROLLBACK_ENABLED=true
  echo "A completed API deployment is available; automatic rollback is enabled."
else
  echo "No completed API deployment exists; automatic rollback is disabled for this bootstrap deployment."
fi

if ecs_service_has_completed_deployment "$WORKER_SERVICE_NAME" "$ECS_SERVICE_STATE"; then
  WORKER_ROLLBACK_ENABLED=true
  echo "A completed worker deployment is available; automatic rollback is enabled."
else
  echo "No completed worker deployment exists; automatic rollback is disabled for this bootstrap deployment."
fi

# Re-read the existing vault and regenerate its immutable-key override before
# the complete plan. This handles workflow retries and state reconciliation.
configure_existing_backup_vault_override
reconcile_existing_retained_resources

# Build a saved final plan, inspect it, and refuse to run any plan that contains
# a delete action for the retained Backup vault.
FINAL_PLAN_FILE="$(mktemp)"
rm -f "$FINAL_PLAN_FILE"

terraform -chdir="$TF" plan \
  -input=false \
  -lock-timeout=5m \
  -var-file="$TFVARS" \
  -var="backend_image=$BACKEND_REPOSITORY:$TAG" \
  -var="backend_rollback_enabled=$BACKEND_ROLLBACK_ENABLED" \
  -var="worker_rollback_enabled=$WORKER_ROLLBACK_ENABLED" \
  -out="$FINAL_PLAN_FILE"

if terraform -chdir="$TF" show -json "$FINAL_PLAN_FILE" |
  jq -e '
    any(
      .resource_changes[]?;
      .address == "module.backup.aws_backup_vault.this"
      and (.change.actions | index("delete")) != null
    )
  ' >/dev/null; then
  echo "Refusing to apply: Terraform still plans to delete or replace the retained AWS Backup vault." >&2
  echo "Expected temporary override file: ${BACKUP_OVERRIDE_FILE}" >&2
  terraform -chdir="$TF" show "$FINAL_PLAN_FILE" >&2
  exit 1
fi

echo "Final plan verified: retained Backup vault has no delete action."

# Update the API, worker, scheduler, and remaining infrastructure only after the
# backward-compatible migration succeeds and the vault safety gate passes.
set +e
terraform -chdir="$TF" apply \
  -input=false \
  -lock-timeout=5m \
  "$FINAL_PLAN_FILE"
FINAL_APPLY_STATUS="$?"
set -e

if [[ "$FINAL_APPLY_STATUS" -ne 0 ]]; then
  report_ecs_service_diagnostics \
    "$CLUSTER_ARN" \
    "$API_SERVICE_NAME" \
    "$WORKER_SERVICE_NAME"
  exit "$FINAL_APPLY_STATUS"
fi

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

INVALIDATION_ID="$(
  aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths '/*' \
    --query 'Invalidation.Id' \
    --output text
)"

[[ -n "$INVALIDATION_ID" && "$INVALIDATION_ID" != "None" ]] || {
  echo "CloudFront did not return an invalidation ID." >&2
  exit 1
}

aws cloudfront wait invalidation-completed \
  --distribution-id "$DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID"

CLOUDFRONT_URL="$(
  terraform -chdir="$TF" output \
    -raw cloudfront_url
)"

smoke_test_json() {
  local path="$1"
  local jq_filter="$2"
  local cookie="${3:-}"
  local response=""
  local response_status=1
  local -a curl_arguments=(
    --fail
    --silent
    --show-error
    --connect-timeout 10
    --max-time 20
    --header "Accept: application/json"
  )

  if [[ -n "$cookie" ]]; then
    curl_arguments+=(--cookie "$cookie")
  fi

  for attempt in $(seq 1 12); do
    set +e
    response="$(curl "${curl_arguments[@]}" "${CLOUDFRONT_URL}${path}" 2>&1)"
    response_status="$?"
    set -e

    if [[ "$response_status" -eq 0 ]] &&
      jq -e "$jq_filter" <<<"$response" >/dev/null 2>&1; then
      echo "Deployment smoke test passed: ${path}"
      return 0
    fi

    echo "Deployment smoke test is not ready for ${path}; retrying in 10 seconds (${attempt}/12)." >&2

    if [[ "$attempt" -lt 12 ]]; then
      sleep 10
    fi
  done

  echo "Deployment smoke test failed for ${CLOUDFRONT_URL}${path}." >&2
  printf '%s\n' "$response" >&2
  return 1
}

# Readiness proves the running API task can reach the session database. The
# invalid session exercises the exact browser failure that previously caused
# DRF to return 500 before the public authentication view could execute.
smoke_test_json \
  "/api/readiness/" \
  '.status == "ready" and .service == "demand-gig-backend"'

smoke_test_json \
  "/api/auth/config/" \
  '.authenticated == false and (.providers | type == "array") and (.csrf_token | type == "string")' \
  "sessionid=00000000000000000000000000000000"

terraform -chdir="$TF" output
