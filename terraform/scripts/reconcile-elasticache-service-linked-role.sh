#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Reconciles the account-wide Amazon ElastiCache service-linked role
# with Terraform state and verifies the AWS-owned trust and managed policy.

set -Eeuo pipefail

MODE="${1:-reconcile}"
ACCOUNT_TERRAFORM_DIR="${2:-terraform/global/account}"

RESOURCE_ADDRESS="aws_iam_service_linked_role.elasticache"
ROLE_NAME="AWSServiceRoleForElastiCache"
SERVICE_NAME="elasticache.amazonaws.com"
POLICY_NAME="ElastiCacheServiceRolePolicy"

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "::error::Required command is not installed: ${command_name}" >&2
    exit 1
  fi
}

require_command aws
require_command terraform

role_arn() {
  aws iam get-role \
    --role-name "${ROLE_NAME}" \
    --query 'Role.Arn' \
    --output text
}

reconcile_role() {
  if terraform -chdir="${ACCOUNT_TERRAFORM_DIR}" state show \
    "${RESOURCE_ADDRESS}" >/dev/null 2>&1; then
    echo "${RESOURCE_ADDRESS} is already managed by the account-foundation state."
    return
  fi

  local error_file
  local existing_role_arn
  local status

  error_file="$(mktemp)"

  set +e
  existing_role_arn="$(
    aws iam get-role \
      --role-name "${ROLE_NAME}" \
      --query 'Role.Arn' \
      --output text \
      2>"${error_file}"
  )"
  status="$?"
  set -e

  if [[ "${status}" -eq 0 ]]; then
    rm -f "${error_file}"
    echo "Importing existing ${ROLE_NAME} into the account-foundation state."

    terraform -chdir="${ACCOUNT_TERRAFORM_DIR}" import \
      -input=false \
      "${RESOURCE_ADDRESS}" \
      "${existing_role_arn}"

    return
  fi

  if grep -qE 'NoSuchEntity|cannot be found' "${error_file}"; then
    rm -f "${error_file}"
    echo "${ROLE_NAME} does not exist. Terraform will create it during apply."
    return
  fi

  cat "${error_file}" >&2
  rm -f "${error_file}"
  echo "::error::Unable to inspect ${ROLE_NAME}." >&2
  exit "${status}"
}

verify_role() {
  local existing_role_arn
  local partition
  local expected_policy_arn
  local trusted_services
  local attached_policy

  existing_role_arn="$(role_arn)"
  partition="$(cut -d: -f2 <<<"${existing_role_arn}")"
  expected_policy_arn="arn:${partition}:iam::aws:policy/aws-service-role/${POLICY_NAME}"

  trusted_services="$(
    aws iam get-role \
      --role-name "${ROLE_NAME}" \
      --query 'Role.AssumeRolePolicyDocument.Statement[].Principal.Service' \
      --output text
  )"

  attached_policy="$(
    aws iam list-attached-role-policies \
      --role-name "${ROLE_NAME}" \
      --query "AttachedPolicies[?PolicyArn=='${expected_policy_arn}'].PolicyArn | [0]" \
      --output text
  )"

  if [[ " ${trusted_services} " != *" ${SERVICE_NAME} "* ]]; then
    echo "::error::${ROLE_NAME} does not trust ${SERVICE_NAME}." >&2
    exit 1
  fi

  if [[ "${attached_policy}" != "${expected_policy_arn}" ]]; then
    echo "::error::${ROLE_NAME} is missing ${expected_policy_arn}." >&2
    exit 1
  fi

  echo "${ROLE_NAME} is valid:"
  echo "- ARN: ${existing_role_arn}"
  echo "- Trusted service: ${SERVICE_NAME}"
  echo "- Managed policy: ${expected_policy_arn}"

  # IAM changes are eventually consistent. Wait before the workload stack asks
  # ElastiCache to create the encrypted Redis/Valkey replication group.
  echo "Waiting 45 seconds for IAM propagation."
  sleep 45
}

case "${MODE}" in
  reconcile)
    reconcile_role
    ;;
  verify)
    verify_role
    ;;
  *)
    echo "Usage: $0 [reconcile|verify] [terraform-account-directory]" >&2
    exit 2
    ;;
esac
