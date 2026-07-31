# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the github oidc Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `role_arn`: ARN of the environment image-and-service release role.
output "role_arn" {
  description = "ARN of the environment image-and-service release role."
  value       = aws_iam_role.github.arn
}
