#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Destroys a Terraform environment while preserving resources that
# the provider refuses to delete. Failed resources are temporarily removed
# from state, the remaining environment is destroyed, and the preserved
# objects are imported back so future deployments continue managing them.

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

for command_name in terraform jq awk sed sort comm grep cut tee; do
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
DESTROY_LOG_DIR="${TF_DIR}/destroy-logs"
MAX_PASSES="${DESTROY_MAX_PASSES:-10}"

mkdir -p "${DESTROY_LOG_DIR}"

COMMON_DESTROY_ARGS=(
  -input=false
  -auto-approve
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

managed_state_list() {
  terraform -chdir="${TF_DIR}" state list 2>/dev/null |
    awk '
      !/(^|\.)data\./ && NF {
        print
      }
    ' |
    sort -u
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

failed_resource_addresses() {
  local log_file="$1"

  # Terraform provider errors normally identify the failing state address as:
  #   with module.example.aws_resource.name,
  sed -nE \
    's/^.*with[[:space:]]+([^,]+),[[:space:]]*$/\1/p' \
    "${log_file}" |
    awk 'NF' |
    sort -u
}

record_and_forget_failed_resource() {
  local address="$1"
  local resource_id

  if ! managed_state_list | grep -Fxq "${address}"; then
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

  printf '%s\t%s\n' "${address}" "${resource_id}" >> "${PRESERVED_FILE}"

  echo "::warning::Preserving ${address} with import ID ${resource_id}."
  echo "::warning::The remote object remains in AWS and may continue generating charges."

  terraform -chdir="${TF_DIR}" state rm \
    -lock-timeout=5m \
    "${address}"
}

reimport_preserved_resources() {
  local address
  local resource_id
  local import_failures=0

  [[ -s "${PRESERVED_FILE}" ]] || return 0

  echo "Re-importing preserved resources so future deployments continue managing them."

  while IFS=$'\t' read -r address resource_id; do
    [[ -n "${address}" && -n "${resource_id}" ]] || continue

    if managed_state_list | grep -Fxq "${address}"; then
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
    echo "::error::One or more preserved AWS resources are not managed by Terraform." >&2
    exit 1
  fi
}

verify_remaining_state() {
  local actual_file
  local expected_file
  local unexpected_file
  local missing_file

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
    echo "::error::Preserved resources were not restored to Terraform state:" >&2
    sed 's/^/- /' "${missing_file}" >&2
    rm -f "${actual_file}" "${expected_file}" "${unexpected_file}" "${missing_file}"
    return 1
  fi

  if [[ -s "${expected_file}" ]]; then
    echo "Infrastructure was destroyed except for these preserved resources:"
    sed 's/^/- /' "${expected_file}"

    append_summary ""
    append_summary "### Preserved AWS resources"
    append_summary ""
    while IFS= read -r address; do
      append_summary "- \`${address}\`"
    done < "${expected_file}"
    append_summary ""
    append_summary "These objects remain in AWS and remain tracked in Terraform state."
  else
    echo "No workload resources remain in Terraform state."
  fi

  rm -f "${actual_file}" "${expected_file}" "${unexpected_file}" "${missing_file}"
}

if [[ "${MODE}" == "verify" ]]; then
  verify_remaining_state
  exit $?
fi

: > "${PRESERVED_FILE}"
destroy_succeeded=false

for pass in $(seq 1 "${MAX_PASSES}"); do
  log_file="${DESTROY_LOG_DIR}/${ENVIRONMENT}-destroy-pass-${pass}.log"

  echo "Terraform destroy pass ${pass}/${MAX_PASSES}."

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
    echo "::error::Review ${log_file} for the complete provider error." >&2
    exit "${destroy_status}"
  fi

  skipped_this_pass=0

  for address in "${failed_addresses[@]}"; do
    if record_and_forget_failed_resource "${address}"; then
      skipped_this_pass=$((skipped_this_pass + 1))
    fi
  done

  if (( skipped_this_pass == 0 )); then
    echo "::error::Destroy made no progress while preserving failed resources." >&2
    exit "${destroy_status}"
  fi

  echo "Retrying without ${skipped_this_pass} preserved resource(s)."
done

if [[ "${destroy_succeeded}" != "true" ]]; then
  echo "::error::Destroy did not complete after ${MAX_PASSES} passes." >&2
  exit 1
fi

reimport_preserved_resources
verify_remaining_state

echo "Tolerant Terraform destroy completed."
