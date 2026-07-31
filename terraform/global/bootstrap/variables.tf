# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares Terraform configuration for variables.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `aws_region`: AWS region in which regional workload resources are created.
variable "aws_region" {
  type = string
}
# Input `environment`: Deployment environment name or the container environment-variable map, according to module context.
variable "environment" {
  type = string
}
# Input `project_name`: Stable project prefix used to name and tag shared AWS resources.
variable "project_name" {
  type = string
  default = "demand-gig-engine"
}
