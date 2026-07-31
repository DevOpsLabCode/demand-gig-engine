# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Configures primary and us-east-1 AWS provider aliases required by regional services such as CloudFront certificates.
# Reading guide: Each comment explains why the following Terraform block exists.

# Configure the AWS provider connection used by the following resources.
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = merge(var.tags, { Project = var.project_name, Environment = var.environment, ManagedBy = "Terraform", Owner = "DevOps Lab Inc.", Repository = "${var.github_org}/${var.github_repo}" })
  }
}
# CloudFront certificates and CLOUDFRONT-scope WAF ACLs must be created in us-east-1.
provider "aws" {
  alias = "us_east_1"
  region = "us-east-1"
  default_tags {
    tags = merge(var.tags, { Project = var.project_name, Environment = var.environment, ManagedBy = "Terraform", Owner = "DevOps Lab Inc.", Repository = "${var.github_org}/${var.github_repo}" })
  }
}
# Read the active AWS account ID so names, policies, and diagnostics match the credentials running Terraform.
data "aws_caller_identity" "current" {
}
# Read the selected workload region for regional resource configuration and outputs.
data "aws_region" "current" {
}

# Read the active AWS partition so account and service ARNs remain portable.
data "aws_partition" "current" {}
