# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies that the account/region GuardDuty detector managed by terraform/global/account is available.

# GuardDuty is an account/region singleton. Read it rather than creating a detector in every environment state.
data "aws_guardduty_detector" "this" {
  count = var.enabled ? 1 : 0
}
