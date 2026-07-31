# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the acm Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `certificate_arn`: ACM certificate ARN used to terminate TLS.
output "certificate_arn" {
  value = try(aws_acm_certificate_validation.this[0].certificate_arn,null)
}
