# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Enables or reuses the regional GuardDuty detector for continuous threat-intelligence findings.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws guardduty detector resource owned by this file.
resource "aws_guardduty_detector" "this" {
  count = var.enabled ? 1 :0
  enable = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  tags = var.tags
}
