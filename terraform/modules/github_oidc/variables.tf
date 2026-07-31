# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares exact GitHub repository subjects and least-privilege deployment targets for AWS federation.

variable "name" {
  type        = string
  description = "IAM role and OIDC resource name prefix."

  validation {
    condition     = length(trimspace(var.name)) >= 3 && length(var.name) <= 64
    error_message = "name must contain 3-64 characters."
  }
}

variable "github_org" {
  type        = string
  description = "GitHub organization embedded in trusted OIDC subjects."

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+$", var.github_org))
    error_message = "github_org contains unsupported characters."
  }
}

variable "github_repo" {
  type        = string
  description = "GitHub repository embedded in trusted OIDC subjects."

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+$", var.github_repo))
    error_message = "github_repo contains unsupported characters."
  }
}

variable "ecr_arns" {
  type        = list(string)
  description = "Exact ECR repository ARNs controlled by the application deployment role."

  validation {
    condition     = length(var.ecr_arns) > 0 && alltrue([for arn in var.ecr_arns : can(regex(":ecr:[^:]+:[0-9]{12}:repository/", arn))])
    error_message = "ecr_arns must contain at least one ECR repository ARN."
  }
}

variable "cluster_arn" {
  type        = string
  description = "ECS cluster ARN used to scope service update permissions."

  validation {
    condition     = can(regex(":ecs:[^:]+:[0-9]{12}:cluster/", var.cluster_arn))
    error_message = "cluster_arn must be an ECS cluster ARN."
  }
}

variable "allowed_branches" {
  type        = set(string)
  description = "Branches encoded in GitHub OIDC subject conditions."
  default     = []

  validation {
    condition     = alltrue([for branch in var.allowed_branches : trimspace(branch) != "" && !contains(["*", "refs/heads/*"], branch)])
    error_message = "allowed_branches must contain only explicit non-wildcard branch names."
  }
}

variable "allowed_environments" {
  type        = set(string)
  description = "Protected GitHub environments encoded in OIDC subject conditions."
  default     = ["dev", "prod"]

  validation {
    condition     = alltrue([for environment in var.allowed_environments : trimspace(environment) != "" && environment != "*"])
    error_message = "allowed_environments must contain explicit non-wildcard names."
  }
}

variable "allow_pull_requests" {
  type        = bool
  description = "Trust pull_request OIDC subjects. Disabled by default because unprotected PR contexts should not receive deployment credentials."
  default     = false
}

variable "permissions_boundary_arn" {
  type        = string
  description = "AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role."

  validation {
    condition     = can(regex("^arn:[^:]+:iam::aws:policy/PowerUserAccess$", var.permissions_boundary_arn))
    error_message = "permissions_boundary_arn must be the partition-correct AWS-managed PowerUserAccess policy ARN."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}

check "trusted_subjects" {
  assert {
    condition     = length(var.allowed_branches) > 0 || length(var.allowed_environments) > 0 || var.allow_pull_requests
    error_message = "At least one explicit branch, protected environment, or deliberately enabled pull-request subject is required."
  }
}
