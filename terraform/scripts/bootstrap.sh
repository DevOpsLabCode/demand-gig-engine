#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates or verifies the remote-state bootstrap stack and writes backend configuration for a target environment.
# Execution model: fail fast, validate prerequisites, run each documented phase, and surface errors.

set -Eeuo pipefail

ENVIRONMENT="${1:-dev}"
[[ "$ENVIRONMENT" =~ ^(dev|prod)$ ]] || { echo "Usage: $0 dev|prod" >&2; exit 2; }
for command_name in aws jq; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required" >&2; exit 1; }
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="demand-gig-engine-${ENVIRONMENT}-${ACCOUNT_ID}-tfstate"

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [[ "${CREATE_BACKEND:-true}" != "true" ]]; then
    echo "Terraform state bucket $BUCKET does not exist. Run bootstrap.sh once with CREATE_BACKEND=true." >&2
    exit 1
  fi
  echo "Creating Terraform state bucket $BUCKET" >&2
  if [[ "$REGION" == "us-east-1" ]]; then
    # Call AWS using the active identity and fail if the requested cloud operation is not
    # authorized.
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  else
    # Call AWS using the active identity and fail if the requested cloud operation is not
    # authorized.
    aws s3api create-bucket \
      --bucket "$BUCKET" \
      --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
  fi
fi

# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3api put-bucket-ownership-controls \
  --bucket "$BUCKET" \
  --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
  'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3api put-bucket-encryption \
  --bucket "$BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3api put-bucket-lifecycle-configuration \
  --bucket "$BUCKET" \
  --lifecycle-configuration \
  '{"Rules":[{"ID":"expire-noncurrent-state","Status":"Enabled","Filter":{"Prefix":""},"NoncurrentVersionExpiration":{"NoncurrentDays":90}}]}'

POLICY_FILE="$(mktemp)"
trap 'rm -f "$POLICY_FILE"' EXIT
jq -n --arg bucket "$BUCKET" '{
  Version: "2012-10-17",
  Statement: [{
    Sid: "DenyInsecureTransport",
    Effect: "Deny",
    Principal: "*",
    Action: "s3:*",
    Resource: ["arn:aws:s3:::" + $bucket, "arn:aws:s3:::" + $bucket + "/*"],
    Condition: {Bool: {"aws:SecureTransport": "false"}}
  }]
}' > "$POLICY_FILE"
# Call AWS using the active identity and fail if the requested cloud operation is not authorized.
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "file://$POLICY_FILE"

BACKEND_FILE="$ROOT/envs/$ENVIRONMENT/backend.hcl"
cat > "$BACKEND_FILE" <<EOF_BACKEND
bucket       = "$BUCKET"
key          = "$ENVIRONMENT/terraform.tfstate"
region       = "$REGION"
encrypt      = true
use_lockfile = true
EOF_BACKEND

printf '%s\n' "$BACKEND_FILE"
