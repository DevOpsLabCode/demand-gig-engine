#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provisions or verifies a KMS-encrypted Terraform backend through the dedicated global/bootstrap Terraform root.
# Execution model: fail closed, never create state infrastructure ad hoc, and migrate first-run bootstrap state into the protected backend.

set -Eeuo pipefail

ENVIRONMENT="${1:-dev}"
[[ "$ENVIRONMENT" =~ ^(account|dev|prod)$ ]] || { echo "Usage: $0 account|dev|prod" >&2; exit 2; }
for command_name in aws terraform; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required" >&2; exit 1; }
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP_DIR="$ROOT/global/bootstrap"
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-demand-gig-engine}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-${ACCOUNT_ID}-tfstate"
KMS_ALIAS="alias/${PROJECT_NAME}-${ENVIRONMENT}-tfstate"
CREATE_BACKEND="${CREATE_BACKEND:-true}"

BOOTSTRAP_BACKEND_FILE="$BOOTSTRAP_DIR/backend-${ENVIRONMENT}.hcl"
if [[ "$ENVIRONMENT" == "account" ]]; then
  CONSUMER_BACKEND_FILE="$ROOT/global/account/backend.hcl"
  CONSUMER_STATE_KEY="account-foundation/terraform.tfstate"
else
  CONSUMER_BACKEND_FILE="$ROOT/envs/$ENVIRONMENT/backend.hcl"
  CONSUMER_STATE_KEY="$ENVIRONMENT/terraform.tfstate"
fi

write_backend_file() {
  local destination="$1"
  local key="$2"
  local kms_key_arn="$3"
  mkdir -p "$(dirname "$destination")"
  cat > "$destination" <<EOF_BACKEND
bucket       = "$BUCKET"
key          = "$key"
region       = "$REGION"
encrypt      = true
kms_key_id   = "$kms_key_arn"
use_lockfile = true
EOF_BACKEND
}

verify_backend_controls() {
  local versioning encryption
  versioning="$(aws s3api get-bucket-versioning --bucket "$BUCKET" --query Status --output text)"
  [[ "$versioning" == "Enabled" ]] || { echo "Terraform state bucket $BUCKET does not have versioning enabled." >&2; exit 1; }

  aws s3api get-public-access-block --bucket "$BUCKET" >/dev/null
  encryption="$(aws s3api get-bucket-encryption \
    --bucket "$BUCKET" \
    --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm' \
    --output text)"
  [[ "$encryption" == "aws:kms" ]] || { echo "Terraform state bucket $BUCKET must use aws:kms default encryption." >&2; exit 1; }
}

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [[ "$CREATE_BACKEND" != "true" ]]; then
    echo "Terraform state bucket $BUCKET does not exist. Run bootstrap.sh once with trusted credentials and CREATE_BACKEND=true." >&2
    exit 1
  fi

  echo "Provisioning protected Terraform backend $BUCKET through global/bootstrap" >&2
  terraform -chdir="$BOOTSTRAP_DIR" init -backend=false -input=false
  terraform -chdir="$BOOTSTRAP_DIR" apply \
    -auto-approve \
    -input=false \
    -var="aws_region=$REGION" \
    -var="environment=$ENVIRONMENT" \
    -var="project_name=$PROJECT_NAME"

  KMS_KEY_ARN="$(terraform -chdir="$BOOTSTRAP_DIR" output -raw kms_key_arn)"
  write_backend_file "$BOOTSTRAP_BACKEND_FILE" "bootstrap/$ENVIRONMENT/terraform.tfstate" "$KMS_KEY_ARN"

  # Move the local first-run bootstrap state into the bucket it just created.
  terraform -chdir="$BOOTSTRAP_DIR" init \
    -force-copy \
    -migrate-state \
    -input=false \
    -backend-config="$BOOTSTRAP_BACKEND_FILE"
else
  verify_backend_controls
  KMS_KEY_ARN="$(aws kms describe-key --key-id "$KMS_ALIAS" --query KeyMetadata.Arn --output text)"
  [[ "$KMS_KEY_ARN" == arn:*:kms:*:*:key/* ]] || { echo "Unable to resolve protected state key $KMS_ALIAS." >&2; exit 1; }
  write_backend_file "$BOOTSTRAP_BACKEND_FILE" "bootstrap/$ENVIRONMENT/terraform.tfstate" "$KMS_KEY_ARN"

  if [[ "$CREATE_BACKEND" == "true" ]]; then
    terraform -chdir="$BOOTSTRAP_DIR" init \
      -reconfigure \
      -input=false \
      -backend-config="$BOOTSTRAP_BACKEND_FILE"

    if [[ -z "$(terraform -chdir="$BOOTSTRAP_DIR" state list 2>/dev/null)" ]]; then
      echo "Backend bucket exists but bootstrap Terraform state is missing. Import the existing bootstrap resources before continuing; refusing to create a second ownership path." >&2
      exit 1
    fi

    terraform -chdir="$BOOTSTRAP_DIR" apply \
      -auto-approve \
      -input=false \
      -var="aws_region=$REGION" \
      -var="environment=$ENVIRONMENT" \
      -var="project_name=$PROJECT_NAME"
  fi
fi

verify_backend_controls
write_backend_file "$CONSUMER_BACKEND_FILE" "$CONSUMER_STATE_KEY" "$KMS_KEY_ARN"
printf '%s\n' "$CONSUMER_BACKEND_FILE"
