# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the secrets manager Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `secret_arn`: ARN of the secret resource consumed by this module.
output "secret_arn" {
  value = aws_secretsmanager_secret.social.arn
}
