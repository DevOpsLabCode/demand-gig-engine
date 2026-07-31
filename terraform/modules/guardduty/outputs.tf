# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes the shared GuardDuty detector identifier when detection is required.

output "detector_id" {
  description = "ID of the account/region GuardDuty detector, or null when disabled."
  value       = try(data.aws_guardduty_detector.this[0].id, null)
}
