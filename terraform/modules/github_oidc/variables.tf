# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the github oidc Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}

# Input `github_org`: GitHub organization embedded in the trusted OIDC subject patterns.
variable "github_org" {
  type = string
}

# Input `github_repo`: GitHub repository embedded in the trusted OIDC subject patterns.
variable "github_repo" {
  type = string
}

# Input `ecr_arns`: ARNs of all ECR repositories controlled by the deployment role.
variable "ecr_arns" {
  type = list(string)
}

# Input `cluster_arn`: ARN of the ECS cluster that will run this service.
variable "cluster_arn" {
  type = string
}

# Input `allowed_branches`: Branches encoded in the GitHub OIDC trust-policy subject conditions.
variable "allowed_branches" {
  type    = set(string)
  default = ["main"]
}

# Input `allowed_environments`: Protected GitHub environments encoded in the OIDC trust-policy subject conditions.
variable "allowed_environments" {
  type    = set(string)
  default = ["dev", "prod"]
}

# Input `allow_pull_requests`: Whether pull-request subjects are included in the GitHub OIDC trust policy.
variable "allow_pull_requests" {
  type    = bool
  default = true
}

# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type    = map(string)
  default = {}
}
