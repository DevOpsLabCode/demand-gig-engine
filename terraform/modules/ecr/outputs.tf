# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the ecr Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `repository_urls`: Map of repository names to ECR push/pull URLs.
output "repository_urls" {
  value = { for k, v in aws_ecr_repository.this : k => v.repository_url }
}
# Output `repository_arns`: ARNs of the ECR repositories for IAM policy construction.
output "repository_arns" {
  value = [for v in aws_ecr_repository.this : v.arn]
}
