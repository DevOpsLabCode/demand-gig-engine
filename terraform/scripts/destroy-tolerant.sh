#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Destroys every Terraform-managed workload resource by trying normal
# deletion first. When deletion fails, the exact failed resource is retried
# individually. Only resources that still cannot be deleted are temporarily
# removed from state, skipped for the rest of the destroy, and imported back
# so future Terraform runs continue managing them.
#
# The remote-state backend and account-foundation stacks are intentionally
# outside this workload root and are therefore not deleted by this script.

set -Eeuo pipefail

ENVIRONMENT="${1:-}"
MODE="${2:-destroy}"

if [[ -z "${ENVIRONMENT}" ]]; then
  echo "Usage: $0 <environment> [destroy|verify]" >&2
  exit 2
fi

case "${ENVIRONMENT}" in
  dev|prod)
    ;;
  *)
    echo "Unsupported environment: ${ENVIRONMENT}" >&2
    exit 2
    ;;
esac

case "${MODE}" in
  destroy|verify)
    ;;
  *)
    echo "Unsupported mode: ${MODE}" >&2
    exit 2
    ;;
esac

for command_name in \
  terraform jq awk sed sort comm grep cut tee seq head sleep mktemp; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command is not installed: ${command_name}" >&2
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
VAR_FILE="envs/${ENVIRONMENT}/terraform.tfvars"
PRESERVED_FILE="${TF_DIR}/${ENVIRONMENT}-preserved-destroy-resources.tsv"
PRESERVED_REASON_FILE="${TF_DIR}/${ENVIRONMENT}-preserved-destroy-reasons.tsv"
DESTROY_LOG_DIR="${TF_DIR}/destroy-logs"

MAX_PASSES="${DESTROY_MAX_PASSES:-10}"
DELETE_RETRY_ATTEMPTS="${DESTROY_DELETE_RETRY_ATTEMPTS:-2}"
DELETE_RETRY_DELAY_SECONDS="${DESTROY_DELETE_RETRY_DELAY_SECONDS:-10}"
PRESERVE_RETAINED_RESOURCES="${DESTROY_PRESERVE_RETAINED_RESOURCES:-true}"

if [[ ! "${MAX_PASSES}" =~ ^[1-9][0-9]*$ ]]; then
  echo "DESTROY_MAX_PASSES must be a positive integer." >&2
  exit 2
fi

if [[ ! "${DELETE_RETRY_ATTEMPTS}" =~ ^[0-9]+$ ]]; then
  echo "DESTROY_DELETE_RETRY_ATTEMPTS must be a non-negative integer." >&2
  exit 2
fi

if [[ ! "${DELETE_RETRY_DELAY_SECONDS}" =~ ^[0-9]+$ ]]; then
  echo "DESTROY_DELETE_RETRY_DELAY_SECONDS must be a non-negative integer." >&2
  exit 2
fi

case "${PRESERVE_RETAINED_RESOURCES,,}" in
  true|false)
    ;;
  *)
    echo "DESTROY_PRESERVE_RETAINED_RESOURCES must be true or false." >&2
    exit 2
    ;;
esac

mkdir -p "${DESTROY_LOG_DIR}"

COMMON_DESTROY_ARGS=(
  -input=false
  -auto-approve
  -no-color
  -lock-timeout=5m
  -var-file="${VAR_FILE}"
  -var="backend_image=public.ecr.aws/docker/library/python:3.12-slim"
)

COMMON_IMPORT_ARGS=(
  -input=false
  -lock-timeout=5m
  -var-file="${VAR_FILE}"
  -var="backend_image=public.ecr.aws/docker/library/python:3.12-slim"
)

REIMPORT_COMPLETED=false

managed_state_list() {
  terraform -chdir="${TF_DIR}" state list 2>/dev/null |
    awk '
      !/(^|\.)data\./ && NF {
        print
      }
    ' |
    sort -u
}

state_contains() {
  local address="$1"

  managed_state_list | grep -Fxq "${address}"
}

manifest_addresses() {
  if [[ -s "${PRESERVED_FILE}" ]]; then
    cut -f1 "${PRESERVED_FILE}" | sort -u
  fi
}

append_summary() {
  local message="$1"

  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf '%s\n' "${message}" >> "${GITHUB_STEP_SUMMARY}"
  fi
}

resource_id_from_state() {
  local address="$1"

  terraform -chdir="${TF_DIR}" show -json |
    jq -er \
      --arg address "${address}" '
        def modules:
          ., (.child_modules[]? | modules);

        .values.root_module
        | modules
        | .resources[]?
        | select(.address == $address)
        | .values.id
        | select(. != null)
        | tostring
      ' |
    head -n 1
}

state_addresses_for_identifier() {
  local identifier="$1"

  terraform -chdir="${TF_DIR}" show -json |
    jq -r \
      --arg identifier "${identifier}" '
        def modules:
          ., (.child_modules[]? | modules);

        .values.root_module
        | modules
        | .resources[]?
        | select(.mode == "managed")
        | select(
            ((.values.id? // "") | tostring) == $identifier
            or ((.values.name? // "") | tostring) == $identifier
            or ((.values.arn? // "") | tostring) == $identifier
          )
        | .address
      '
}

known_address_for_delete_error() {
  local resource_type="$1"
  local identifier="$2"
  local address=""

  case "${resource_type}" in
    "Backup Vault")
      address="module.backup.aws_backup_vault.this"
      ;;
    "S3 Bucket")
      # The retained CloudTrail bucket is intentionally not emptied during
      # teardown because it contains audit records and versioned objects.
      if [[ "${identifier}" == *-cloudtrail ]]; then
        address="module.cloudtrail.aws_s3_bucket.logs"
      fi
      ;;
  esac

  if [[ -n "${address}" ]] && state_contains "${address}"; then
    printf '%s\n' "${address}"
  fi
}

failed_resource_addresses() {
  local log_file="$1"
  local resource_type
  local identifier
  local mapped_address

  {
    # Most Terraform provider errors include the exact state address:
    #
    #   with module.example.aws_resource.name,
    sed -nE \
      's/^.*with[[:space:]]+([^,]+),[[:space:]]*$/\1/p' \
      "${log_file}"

    # Some provider delete errors omit the "with ..." line. Parse both the AWS
    # resource type and identifier, then resolve them through state. When state
    # JSON cannot be matched reliably after a partial destroy, use the
    # configuration's known retained-resource addresses as a safe fallback.
    while IFS=$'\t' read -r resource_type identifier; do
      [[ -n "${resource_type}" && -n "${identifier}" ]] || continue

      mapped_address="$(
        state_addresses_for_identifier "${identifier}" |
          head -n 1
      )"

      if [[ -n "${mapped_address}" ]]; then
        printf '%s\n' "${mapped_address}"
        continue
      fi

      known_address_for_delete_error \
        "${resource_type}" \
        "${identifier}"
    done < <(
      sed -nE \
        's/^.*Error: deleting ([^(]+) \((.*)\):.*$/\1\t\2/p' \
        "${log_file}" |
        awk 'NF' |
        sort -u
    )

    # Last-resort exact signatures. These are deliberately narrow so the
    # tolerant destroy never skips an unrelated resource.
    if grep -Fq \
      "Backup vault cannot be deleted because it contains recovery points" \
      "${log_file}"; then
      if state_contains "module.backup.aws_backup_vault.this"; then
        printf '%s\n' "module.backup.aws_backup_vault.this"
      fi
    fi

    if grep -Fq "api error BucketNotEmpty" "${log_file}" &&
       grep -Eq 'Error: deleting S3 Bucket \([^)]*-cloudtrail\)' "${log_file}"; then
      if state_contains "module.cloudtrail.aws_s3_bucket.logs"; then
        printf '%s\n' "module.cloudtrail.aws_s3_bucket.logs"
      fi
    fi
  } |
    awk 'NF' |
    sort -u
}

failure_reason_for_address() {
  local address="$1"
  local log_file="$2"
  local reason=""

  if [[ "${address}" == "module.backup.aws_backup_vault.this" ]] &&
     grep -Fq \
       "Backup vault cannot be deleted because it contains recovery points" \
       "${log_file}"; then
    reason="Backup vault contains recovery points"
  elif [[ "${address}" == "module.cloudtrail.aws_s3_bucket.logs" ]] &&
       grep -Fq "api error BucketNotEmpty" "${log_file}"; then
    reason="CloudTrail bucket contains audit objects or object versions"
  else
    reason="$(
      sed -nE \
        's/^.*Error:[[:space:]]*(.*)$/\1/p' \
        "${log_file}" |
        head -n 1
    )"
  fi

  reason="${reason//$'\t'/ }"
  reason="${reason//$'\r'/ }"
  reason="${reason//$'\n'/ }"

  printf '%s\n' "${reason:-Terraform provider refused deletion}"
}

failure_is_non_retryable() {
  local address="$1"
  local log_file="$2"

  # A Backup vault with recovery points will continue to fail until the
  # recovery points expire or are explicitly deleted.
  if [[ "${address}" == "module.backup.aws_backup_vault.this" ]] &&
     grep -Fq \
       "Backup vault cannot be deleted because it contains recovery points" \
       "${log_file}"; then
    return 0
  fi

  # The CloudTrail bucket intentionally retains audit data and versions. Do not
  # empty it during an environment teardown merely to make DeleteBucket pass.
  if [[ "${address}" == "module.cloudtrail.aws_s3_bucket.logs" ]] &&
     grep -Fq "api error BucketNotEmpty" "${log_file}"; then
    return 0
  fi

  return 1
}

retry_failed_resource_delete() {
  local address="$1"
  local parent_pass="$2"
  local attempt
  local log_file
  local destroy_status
  local safe_address

  if ! state_contains "${address}"; then
    echo "Resource was already deleted: ${address}"
    return 0
  fi

  if (( DELETE_RETRY_ATTEMPTS == 0 )); then
    echo "Individual delete retry is disabled for ${address}."
    return 1
  fi

  safe_address="$(
    printf '%s' "${address}" |
      sed -E 's/[^A-Za-z0-9_.-]+/_/g'
  )"

  for attempt in $(seq 1 "${DELETE_RETRY_ATTEMPTS}"); do
    log_file="${DESTROY_LOG_DIR}/${ENVIRONMENT}-destroy-pass-${parent_pass}-retry-${safe_address}-${attempt}.log"

    echo "Retrying deletion of ${address} (${attempt}/${DELETE_RETRY_ATTEMPTS})."

    set +e
    terraform -chdir="${TF_DIR}" destroy \
      "${COMMON_DESTROY_ARGS[@]}" \
      -target="${address}" \
      2>&1 | tee "${log_file}"
    destroy_status="${PIPESTATUS[0]}"
    set -e

    if [[ "${destroy_status}" -eq 0 ]] || ! state_contains "${address}"; then
      echo "Deletion succeeded for ${address}."
      return 0
    fi

    if (( attempt < DELETE_RETRY_ATTEMPTS && DELETE_RETRY_DELAY_SECONDS > 0 )); then
      echo "Deletion still failed for ${address}; waiting ${DELETE_RETRY_DELAY_SECONDS} seconds before retry."
      sleep "${DELETE_RETRY_DELAY_SECONDS}"
    fi
  done

  echo "::warning::Deletion remained unsuccessful for ${address} after ${DELETE_RETRY_ATTEMPTS} individual attempt(s)."
  return 1
}

record_and_forget_resource() {
  local address="$1"
  local reason="${2:-Terraform provider refused deletion}"
  local resource_id

  if ! state_contains "${address}"; then
    echo "Failed resource is no longer present in state: ${address}"
    return 1
  fi

  if grep -Fq "${address}"$'\t' "${PRESERVED_FILE}" 2>/dev/null; then
    echo "Resource was already selected for preservation: ${address}"
    return 1
  fi

  resource_id="$(resource_id_from_state "${address}")"

  if [[ -z "${resource_id}" || "${resource_id}" == "null" ]]; then
    echo "::error::Unable to determine an import ID for ${address}; refusing to orphan it." >&2
    return 1
  fi

  # Write the recovery manifest before changing state. If the process receives
  # SIGINT, SIGTERM, or exits unexpectedly, the EXIT trap uses this record to
  # import the resource back.
  printf '%s\t%s\n' "${address}" "${resource_id}" >> "${PRESERVED_FILE}"
  printf '%s\t%s\n' "${address}" "${reason}" >> "${PRESERVED_REASON_FILE}"

  echo "::warning::Temporarily removing ${address} from state so teardown can continue."
  echo "::warning::Reason: ${reason}."
  echo "::warning::Preserving import ID ${resource_id}; the remote object remains in AWS and may continue generating charges."

  if ! terraform -chdir="${TF_DIR}" state rm \
    -lock-timeout=5m \
    "${address}"; then
    echo "::error::Unable to remove ${address} from state for tolerant continuation." >&2
    return 1
  fi
}

preserve_known_retained_resources() {
  local address
  local reason
  local preserved_count=0

  if [[ "${PRESERVE_RETAINED_RESOURCES,,}" != "true" ]]; then
    echo "Proactive retained-resource preservation is disabled."
    return 0
  fi

  echo "Preserving retained data resources before Terraform destroy."

  while IFS=$'\t' read -r address reason; do
    [[ -n "${address}" ]] || continue

    if ! state_contains "${address}"; then
      echo "Retained resource is not currently in state: ${address}"
      continue
    fi

    if record_and_forget_resource "${address}" "${reason}"; then
      preserved_count=$((preserved_count + 1))
    fi
  done <<'EOF'
module.backup.aws_backup_vault.this	Retained AWS Backup vault; recovery points may exist
module.cloudtrail.aws_s3_bucket.logs	Retained CloudTrail audit bucket; objects or object versions may exist
EOF

  echo "Proactively preserved ${preserved_count} retained resource(s)."
}

reimport_preserved_resources() {
  local address
  local resource_id
  local import_failures=0

  [[ -s "${PRESERVED_FILE}" ]] || return 0

  echo "Re-importing skipped resources so future deployments continue managing them."

  while IFS=$'\t' read -r address resource_id; do
    [[ -n "${address}" && -n "${resource_id}" ]] || continue

    if state_contains "${address}"; then
      echo "Preserved resource is already in state: ${address}"
      continue
    fi

    if ! terraform -chdir="${TF_DIR}" import \
      "${COMMON_IMPORT_ARGS[@]}" \
      "${address}" \
      "${resource_id}"; then
      echo "::error::Unable to re-import ${address} using ID ${resource_id}." >&2
      import_failures=$((import_failures + 1))
    fi
  done < "${PRESERVED_FILE}"

  if (( import_failures > 0 )); then
    echo "::error::One or more skipped AWS resources are not managed by Terraform." >&2
    return 1
  fi

  return 0
}

restore_state_on_exit() {
  local original_status="$?"

  trap - EXIT INT TERM HUP

  if [[ "${MODE}" == "destroy" &&
        "${REIMPORT_COMPLETED}" != "true" &&
        -s "${PRESERVED_FILE}" ]]; then
    echo "::warning::Destroy exited before normal completion; restoring skipped resources to Terraform state."

    set +e
    reimport_preserved_resources
    local restore_status="$?"
    set -e

    if [[ "${restore_status}" -ne 0 ]]; then
      original_status=1
    fi
  fi

  exit "${original_status}"
}

verify_remaining_state() {
  local actual_file
  local expected_file
  local unexpected_file
  local missing_file
  local address
  local reason

  actual_file="$(mktemp)"
  expected_file="$(mktemp)"
  unexpected_file="$(mktemp)"
  missing_file="$(mktemp)"

  managed_state_list > "${actual_file}"
  manifest_addresses > "${expected_file}"

  comm -23 "${actual_file}" "${expected_file}" > "${unexpected_file}"
  comm -13 "${actual_file}" "${expected_file}" > "${missing_file}"

  if [[ -s "${unexpected_file}" ]]; then
    echo "::error::Unexpected resources remain in Terraform state:" >&2
    sed 's/^/- /' "${unexpected_file}" >&2
    rm -f "${actual_file}" "${expected_file}" "${unexpected_file}" "${missing_file}"
    return 1
  fi

  if [[ -s "${missing_file}" ]]; then
    echo "::error::Skipped resources were not restored to Terraform state:" >&2
    sed 's/^/- /' "${missing_file}" >&2
    rm -f "${actual_file}" "${expected_file}" "${unexpected_file}" "${missing_file}"
    return 1
  fi

  append_summary ""
  append_summary "### Terraform destroy behavior"
  append_summary ""
  append_summary "- Retained Backup and CloudTrail data resources were preserved before deletion when present."
  append_summary "- Every other workload resource received a normal Terraform delete attempt."
  append_summary "- Other failed resources received up to ${DELETE_RETRY_ATTEMPTS} additional individual delete attempt(s)."

  if [[ -s "${expected_file}" ]]; then
    echo "Infrastructure was destroyed except for resources whose deletion remained unsuccessful:"
    sed 's/^/- /' "${expected_file}"

    append_summary "- Preserved resources were restored to Terraform state after teardown."
    append_summary ""
    append_summary "### Skipped AWS resources"
    append_summary ""

    while IFS= read -r address; do
      reason="$(
        awk -F '\t' \
          -v address="${address}" \
          '$1 == address {
             $1 = ""
             sub(/^\t/, "")
             print
             exit
           }' \
          "${PRESERVED_REASON_FILE}" 2>/dev/null
      )"

      if [[ -n "${reason}" ]]; then
        append_summary "- \`${address}\`: ${reason}"
      else
        append_summary "- \`${address}\`"
      fi
    done < "${expected_file}"

    append_summary ""
    append_summary "These objects remain in AWS and remain tracked in Terraform state."
  else
    echo "All Terraform-managed workload resources were deleted successfully."
    append_summary "- No workload resources required skipping."
  fi

  rm -f "${actual_file}" "${expected_file}" "${unexpected_file}" "${missing_file}"
}

trap restore_state_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

if [[ "${MODE}" == "verify" ]]; then
  REIMPORT_COMPLETED=true
  verify_remaining_state
  exit $?
fi

# A new destroy operation starts with a fresh recovery manifest. Resources are
# added only after both the normal full destroy and individual retry fail.
: > "${PRESERVED_FILE}"
: > "${PRESERVED_REASON_FILE}"

# These data-retention resources are intentionally kept across ephemeral
# environment teardowns. Removing them from state before `terraform destroy`
# prevents predictable BucketNotEmpty and recovery-point deletion failures.
preserve_known_retained_resources

destroy_succeeded=false

for pass in $(seq 1 "${MAX_PASSES}"); do
  log_file="${DESTROY_LOG_DIR}/${ENVIRONMENT}-destroy-pass-${pass}.log"

  echo "Terraform full destroy pass ${pass}/${MAX_PASSES}."
  echo "Every resource still in state will receive a normal deletion attempt."

  set +e
  terraform -chdir="${TF_DIR}" destroy \
    "${COMMON_DESTROY_ARGS[@]}" \
    2>&1 | tee "${log_file}"
  destroy_status="${PIPESTATUS[0]}"
  set -e

  if [[ "${destroy_status}" -eq 0 ]]; then
    destroy_succeeded=true
    break
  fi

  mapfile -t failed_addresses < <(failed_resource_addresses "${log_file}")

  if (( ${#failed_addresses[@]} == 0 )); then
    echo "::error::Destroy failed, but no failing Terraform resource address was found." >&2
    echo "::error::No resource was skipped because deletion failure could not be attributed safely." >&2
    echo "::error::Review ${log_file} for the complete provider error." >&2
    exit "${destroy_status}"
  fi

  deleted_after_retry=0
  skipped_this_pass=0

  for address in "${failed_addresses[@]}"; do
    if ! state_contains "${address}"; then
      echo "Failed address is no longer managed and needs no action: ${address}"
      continue
    fi

    failure_reason="$(
      failure_reason_for_address \
        "${address}" \
        "${log_file}"
    )"

    if failure_is_non_retryable "${address}" "${log_file}"; then
      echo "::warning::Deletion already failed for ${address} with a non-retryable condition."
      echo "::warning::Skipping targeted retries: ${failure_reason}."
    elif retry_failed_resource_delete "${address}" "${pass}"; then
      deleted_after_retry=$((deleted_after_retry + 1))
      continue
    fi

    if record_and_forget_resource \
      "${address}" \
      "${failure_reason}"; then
      skipped_this_pass=$((skipped_this_pass + 1))
    fi
  done

  if (( deleted_after_retry == 0 && skipped_this_pass == 0 )); then
    echo "::error::Destroy made no progress." >&2
    echo "::error::No resource was deleted after retry and no failed resource could be skipped safely." >&2
    exit "${destroy_status}"
  fi

  echo "Pass ${pass} recovery result: ${deleted_after_retry} deleted after retry; ${skipped_this_pass} skipped after unsuccessful deletion."
  echo "Retrying the full destroy for all remaining managed workload resources."
done

if [[ "${destroy_succeeded}" != "true" ]]; then
  echo "::error::Destroy did not complete after ${MAX_PASSES} full passes." >&2
  exit 1
fi

if ! reimport_preserved_resources; then
  exit 1
fi

REIMPORT_COMPLETED=true

verify_remaining_state

echo "Tolerant Terraform destroy completed."
