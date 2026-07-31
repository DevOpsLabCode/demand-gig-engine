# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the ses Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `identity_arn`: ARN of the identity resource consumed by this module.
output "identity_arn" {
  value = try(aws_ses_domain_identity.this[0].arn,null)
}
