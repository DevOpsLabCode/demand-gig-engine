# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the waf Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `arn`: ARN of the CloudFront-scoped Web ACL attached to the distribution.
output "arn" {
  value = aws_wafv2_web_acl.this.arn
}
# Output `id`: Web ACL identifier used by logging and diagnostics.
output "id" {
  value = aws_wafv2_web_acl.this.id
}
