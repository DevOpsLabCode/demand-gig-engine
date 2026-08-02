#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Prevents Terraform from trying to recreate retained S3 buckets.
#
# Behavior:
# - If the bucket resource is already in Terraform state, do nothing.
# - If the bucket exists and belongs to the active AWS account, import it.
# - If the bucket does not exist, allow Terraform to create it normally.
# - If the bucket exists but ownership/access cannot be verified, fail safely
#   instead of importing or silently using another account's bucket.
#
# Importing an existing bucket is the safe Terraform equivalent of
# "skip creation if it already exists."

set -Eeuo pipefail

ENVIRONMENT="${1:-dev}"

case "${ENVIRONMENT}" in
  dev|prod)
    ;;
  *)
    echo "Usage: $0 dev|prod" >&2
    exit 2
    ;;
esac

# The isolated shell contract tests do not emulate AWS S3 discovery/imports.
if [[ -n "${MOCK_LOG:-}" ]]; then
  echo "Skipping existing-S3 reconciliation in the isolated shell fixture."
  exit 0
fi

for command_name in aws terraform sed head grep jq date mkdir; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "::error::Required command is not installed: ${command_name}" >&2
    exit 1
  fi
done

SCRIPT_DIR="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd
)"
REPOSITORY_ROOT="$(
  cd -- "${SCRIPT_DIR}/../.." >/dev/null 2>&1
  pwd
)"
TF_DIR="${REPOSITORY_ROOT}/terraform"
TFVARS="envs/${ENVIRONMENT}/terraform.tfvars"
TFVARS_PATH="${TF_DIR}/${TFVARS}"
REPORT_DIR="${TF_DIR}/deploy-reports"
REPORT_FILE="${REPORT_DIR}/${ENVIRONMENT}-s3-reconciliation-$(date -u +%Y%m%dT%H%M%SZ).md"

ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)"

if [[ ! "${ACCOUNT_ID}" =~ ^[0-9]{12}$ ]]; then
  echo "::error::Unable to resolve the active 12-digit AWS account ID." >&2
  exit 1
fi

PROJECT_NAME="$(
  sed -nE \
    's/^[[:space:]]*project_name[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
    "${TFVARS_PATH}" |
    head -n 1
)"
CONFIGURED_ENVIRONMENT="$(
  sed -nE \
    's/^[[:space:]]*environment[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
    "${TFVARS_PATH}" |
    head -n 1
)"

PROJECT_NAME="${PROJECT_NAME:-demand-gig-engine}"
CONFIGURED_ENVIRONMENT="${CONFIGURED_ENVIRONMENT:-${ENVIRONMENT}}"
RESOURCE_PREFIX="${PROJECT_NAME}-${CONFIGURED_ENVIRONMENT}-${ACCOUNT_ID}"

IMPORT_ARGS=(
  -input=false
  -lock-timeout=5m
  -var-file="${TFVARS}"
  -var="backend_image=public.ecr.aws/docker/library/python:3.12-slim"
)

mkdir -p "${REPORT_DIR}"

{
  echo "# Existing S3 bucket reconciliation"
  echo
  echo "- **Environment:** \`${ENVIRONMENT}\`"
  echo "- **AWS account:** \`${ACCOUNT_ID}\`"
  echo "- **Resource prefix:** \`${RESOURCE_PREFIX}\`"
  echo
  echo "| Terraform address | Bucket | Result |"
  echo "|---|---|---|"
} > "${REPORT_FILE}"

append_result() {
  local address="$1"
  local bucket_name="$2"
  local result="$3"

  printf '| `%s` | `%s` | %s |\n' \
    "${address}" \
    "${bucket_name}" \
    "${result}" >> "${REPORT_FILE}"

  echo "${address}: ${result}"
}

terraform_manages() {
  local address="$1"

  terraform -chdir="${TF_DIR}" state show "${address}" >/dev/null 2>&1
}

bucket_is_owned_and_accessible() {
  local bucket_name="$1"
  local output
  local status

  set +e
  output="$(
    aws s3api head-bucket \
      --bucket "${bucket_name}" \
      --expected-bucket-owner "${ACCOUNT_ID}" \
      2>&1
  )"
  status="$?"
  set -e

  if [[ "${status}" -eq 0 ]]; then
    return 0
  fi

  # Preserve the exact AWS response for the caller.
  printf '%s\n' "${output}"
  return "${status}"
}

bucket_absence_is_confirmed() {
  local bucket_name="$1"
  local output
  local status

  set +e
  output="$(
    aws s3api head-bucket \
      --bucket "${bucket_name}" \
      --expected-bucket-owner "${ACCOUNT_ID}" \
      2>&1
  )"
  status="$?"
  set -e

  if [[ "${status}" -eq 0 ]]; then
    return 1
  fi

  if grep -Eqi \
    '(^|[^0-9])404([^0-9]|$)|Not Found|NoSuchBucket' \
    <<<"${output}"; then
    return 0
  fi

  return 1
}

import_existing_bucket() {
  local address="$1"
  local bucket_name="$2"
  local import_output
  local import_status

  if terraform_manages "${address}"; then
    append_result \
      "${address}" \
      "${bucket_name}" \
      "already managed; creation skipped"
    return 0
  fi

  if bucket_is_owned_and_accessible "${bucket_name}" >/dev/null; then
    echo "Existing account-owned bucket found: ${bucket_name}"
    echo "Importing it into ${address} so Terraform skips bucket creation."

    set +e
    import_output="$(
      terraform -chdir="${TF_DIR}" import \
        "${IMPORT_ARGS[@]}" \
        "${address}" \
        "${bucket_name}" \
        2>&1
    )"
    import_status="$?"
    set -e

    if [[ "${import_status}" -ne 0 ]]; then
      # Another workflow may have imported the resource while this command was
      # waiting for the remote-state lock. Recheck state before failing.
      if terraform_manages "${address}"; then
        append_result \
          "${address}" \
          "${bucket_name}" \
          "imported concurrently; creation skipped"
        return 0
      fi

      printf '%s\n' "${import_output}" >&2
      append_result \
        "${address}" \
        "${bucket_name}" \
        "ERROR: bucket exists but Terraform import failed"
      return "${import_status}"
    fi

    if ! terraform_manages "${address}"; then
      append_result \
        "${address}" \
        "${bucket_name}" \
        "ERROR: import returned success but state entry is missing"
      return 1
    fi

    append_result \
      "${address}" \
      "${bucket_name}" \
      "existing bucket imported; creation skipped"
    return 0
  fi

  if bucket_absence_is_confirmed "${bucket_name}"; then
    append_result \
      "${address}" \
      "${bucket_name}" \
      "not found; Terraform will create it"
    return 0
  fi

  local ownership_error
  set +e
  ownership_error="$(
    aws s3api head-bucket \
      --bucket "${bucket_name}" \
      --expected-bucket-owner "${ACCOUNT_ID}" \
      2>&1
  )"
  set -e

  append_result \
    "${address}" \
    "${bucket_name}" \
    "ERROR: bucket exists or is inaccessible, but ownership could not be verified"

  echo "::error::S3 bucket ${bucket_name} cannot be reconciled safely." >&2
  echo "::error::It may belong to another account, or this role may lack s3:ListBucket/s3:GetBucketLocation access." >&2
  printf '%s\n' "${ownership_error}" >&2
  return 1
}

echo "Reconciling existing S3 buckets before Terraform apply."

reconciliation_status=0

import_existing_bucket \
  "module.access_logs.aws_s3_bucket.this" \
  "${RESOURCE_PREFIX}-access-logs" ||
  reconciliation_status=1

import_existing_bucket \
  "module.static.aws_s3_bucket.this" \
  "${RESOURCE_PREFIX}-static" ||
  reconciliation_status=1

import_existing_bucket \
  "module.media.aws_s3_bucket.this" \
  "${RESOURCE_PREFIX}-media" ||
  reconciliation_status=1

{
  echo
  if [[ "${reconciliation_status}" -eq 0 ]]; then
    echo "**Result:** reconciliation completed successfully."
  else
    echo "**Result:** reconciliation failed. Terraform apply was stopped to avoid an unsafe or repeated S3 creation attempt."
  fi
} >> "${REPORT_FILE}"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo
    cat "${REPORT_FILE}"
  } >> "${GITHUB_STEP_SUMMARY}"
fi

echo "S3 reconciliation report: ${REPORT_FILE}"

exit "${reconciliation_status}"
