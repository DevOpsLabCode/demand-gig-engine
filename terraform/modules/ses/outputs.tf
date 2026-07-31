# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes SES identity and authentication values for operations and application configuration.

output "identity_arn" {
  description = "Terraform-created or externally supplied SES domain identity ARN; null only when outbound email is intentionally disabled."
  value       = var.create_dns ? aws_ses_domain_identity.this[0].arn : var.existing_identity_arn
}

output "mail_from_domain" {
  description = "Custom SES MAIL FROM domain, or null when disabled."
  value       = try(aws_ses_domain_mail_from.this[0].mail_from_domain, null)
}

output "dkim_tokens" {
  description = "SES Easy DKIM tokens, or an empty list when disabled."
  value       = try(aws_ses_domain_dkim.this[0].dkim_tokens, [])
}
