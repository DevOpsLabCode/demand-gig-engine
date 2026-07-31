# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes the created or supplied ACM certificate ARN.

output "certificate_arn" {
  description = "Created and validated ACM certificate ARN, supplied existing ARN, or null when TLS is intentionally not configured."
  value       = var.create ? aws_acm_certificate_validation.this[0].certificate_arn : var.existing_certificate_arn
}
