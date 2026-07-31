# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the guardduty Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `detector_id`: Identifier of the detector resource consumed by this module.
output "detector_id" {
  value = try(aws_guardduty_detector.this[0].id,null)
}
