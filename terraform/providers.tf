provider "aws" {
  region = var.aws_region
  default_tags {
    tags = merge(var.tags, { Project = var.project_name, Environment = var.environment, ManagedBy = "Terraform" })
  }
}
# CloudFront certificates and CLOUDFRONT-scope WAF ACLs must be created in us-east-1.
provider "aws" {
  alias = "us_east_1"
  region = "us-east-1"
  default_tags {
    tags = merge(var.tags, { Project = var.project_name, Environment = var.environment, ManagedBy = "Terraform" })
  }
}
data "aws_caller_identity" "current" {
}
data "aws_region" "current" {
}
