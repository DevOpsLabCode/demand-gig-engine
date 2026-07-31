variable "name" {
  type = string
}

variable "github_org" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "resource_name_prefix" {
  type        = string
  description = "Prefix used to scope IAM role management and PassRole."
}

variable "create_oidc_provider" {
  type        = bool
  description = "Create the account-level GitHub OIDC provider. Enable in only one environment per AWS account."
  default     = true
}

variable "allowed_branches" {
  type    = set(string)
  default = []
}

variable "allowed_environments" {
  type    = set(string)
  default = []
}

variable "allow_pull_requests" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
