#!/usr/bin/env bash
# Diagnose and repair the Amazon RDS service-linked role non-destructively.
# This script creates the role only when it is missing. It never deletes or
# edits an existing service-linked role.

set -Eeuo pipefail

ROLE_NAME="AWSServiceRoleForRDS"
SERVICE_NAME="rds.amazonaws.com"
EXPECTED_PATH="/aws-service-role/rds.amazonaws.com/"
EXPECTED_POLICY="arn:aws:iam::aws:policy/aws-service-role/AmazonRDSServiceRolePolicy"

for command_name in aws jq; do
  command -v "$command_name" >/dev/null || {
    echo "$command_name is required." >&2
    exit 1
  }
done

aws sts get-caller-identity >/dev/null

if ! aws iam get-role \
  --role-name "$ROLE_NAME" \
  >/tmp/rds-service-linked-role.json 2>/tmp/rds-service-linked-role.err; then

  if grep -q "NoSuchEntity" /tmp/rds-service-linked-role.err; then
    echo "Amazon RDS service-linked role is missing. Creating it..."

    aws iam create-service-linked-role \
      --aws-service-name "$SERVICE_NAME" \
      >/tmp/rds-service-linked-role-created.json

    # IAM is eventually consistent. Give the new role time to propagate before
    # a deployment immediately creates an RDS DB Proxy.
    sleep 30

    aws iam get-role \
      --role-name "$ROLE_NAME" \
      >/tmp/rds-service-linked-role.json
  else
    cat /tmp/rds-service-linked-role.err >&2
    exit 1
  fi
fi

ROLE_PATH="$(
  jq -r '.Role.Path' \
    /tmp/rds-service-linked-role.json
)"

TRUST_PRINCIPALS="$(
  jq -r '
    .Role.AssumeRolePolicyDocument.Statement[]
    | select(.Effect == "Allow")
    | .Principal.Service
    | if type == "array" then .[] else . end
  ' /tmp/rds-service-linked-role.json |
    sort -u
)"

ATTACHED_POLICIES="$(
  aws iam list-attached-role-policies \
    --role-name "$ROLE_NAME" \
    --query 'AttachedPolicies[].PolicyArn' \
    --output text
)"

echo "Role path: $ROLE_PATH"
echo "Trusted service principals:"
printf '%s\n' "$TRUST_PRINCIPALS"
echo "Attached policies:"
printf '%s\n' "$ATTACHED_POLICIES"

status=0

if [[ "$ROLE_PATH" != "$EXPECTED_PATH" ]]; then
  echo "::error::Unexpected RDS service-linked role path: $ROLE_PATH" >&2
  status=2
fi

if ! grep -Fxq "$SERVICE_NAME" <<<"$TRUST_PRINCIPALS"; then
  echo "::error::$ROLE_NAME does not trust $SERVICE_NAME." >&2
  status=2
fi

if [[ " $ATTACHED_POLICIES " != *" $EXPECTED_POLICY "* ]]; then
  echo "::error::$ROLE_NAME is missing $EXPECTED_POLICY." >&2
  status=2
fi

if [[ "$status" -ne 0 ]]; then
  cat >&2 <<'EOF'

The existing AWSServiceRoleForRDS is malformed. Amazon RDS service-linked roles
cannot be repaired by editing their trust or permissions policies.

Do not delete it blindly. First inventory every RDS DB instance, cluster, and
proxy in every enabled AWS Region. Delete or migrate all dependent RDS
resources, then delete and recreate the service-linked role using the official
IAM service-linked-role APIs.
EOF
  exit "$status"
fi

echo "AWSServiceRoleForRDS is structurally valid."
echo "Wait at least 30 seconds after first creation, then retry the Terraform deployment."
