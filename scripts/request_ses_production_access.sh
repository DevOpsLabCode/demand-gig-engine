#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Safely request SES production access for Open Concert transactional verification email.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
WEBSITE_URL="${SES_WEBSITE_URL:-https://devopslabinc.com}"
CONTACT_EMAIL="${SES_CONTACT_EMAIL:-hello@devopslabinc.com}"
USE_CASE="${SES_USE_CASE_DESCRIPTION:-Open Concert sends transactional account verification and security email only to users who register, sign in, or explicitly request verification. We do not use purchased lists. Bounce and complaint handling is enforced through Amazon SES and application controls.}"

command -v aws >/dev/null 2>&1 || {
  echo "ERROR: AWS CLI is required."
  exit 2
}

production_access="$(aws sesv2 get-account --region "$REGION" --query 'ProductionAccessEnabled' --output text)"
review_status="$(aws sesv2 get-account --region "$REGION" --query 'Details.ReviewDetails.Status' --output text 2>/dev/null || true)"

if [[ "$production_access" == "True" || "$production_access" == "true" ]]; then
  echo "SES production access is already enabled in $REGION."
  exit 0
fi

case "$review_status" in
  PENDING)
    echo "SES production access request is already pending in $REGION."
    exit 0
    ;;
  GRANTED)
    echo "SES production access review is granted in $REGION. Re-checking account status may take a short time."
    exit 0
    ;;
  DENIED)
    echo "WARNING: SES production access was denied previously in $REGION."
    echo "WARNING: Terraform will continue; review the AWS Support case before requesting production access again."
    echo "WARNING: While SES remains in sandbox, verification email can only be sent to SES-verified recipient addresses."
    exit 0
    ;;
  FAILED)
    echo "Previous SES production-access request failed; submitting a fresh request."
    ;;
esac

aws sesv2 put-account-details \
  --region "$REGION" \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --website-url "$WEBSITE_URL" \
  --contact-language EN \
  --additional-contact-email-addresses "$CONTACT_EMAIL" \
  --use-case-description "$USE_CASE"

echo "SES production-access request submitted for $REGION."
echo "AWS review status can be checked with:"
echo "aws sesv2 get-account --region $REGION --query '{ProductionAccessEnabled:ProductionAccessEnabled,Review:Details.ReviewDetails}'"
