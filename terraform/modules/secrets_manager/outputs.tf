# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the secrets manager Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `secret_arn`: ARN of the secret resource consumed by ECS task definitions.
output "secret_arn" {
  description = "Secrets Manager ARN containing provider credentials."
  value       = aws_secretsmanager_secret.social.arn
  sensitive   = true

  # A targeted migration apply must not expose this ARN until the initial JSON
  # value exists and Secrets Manager has assigned its AWSCURRENT staging label.
  depends_on = [
    aws_secretsmanager_secret_version.initial,
  ]
}
