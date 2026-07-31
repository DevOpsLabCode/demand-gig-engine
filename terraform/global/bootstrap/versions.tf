# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares Terraform configuration for versions.
# Reading guide: Each comment explains why the following Terraform block exists.

# Define Terraform and provider compatibility before any resources are evaluated.
terraform {
  required_version = ">=1.10.0"
  required_providers {
    aws = {source = "hashicorp/aws",version = "~>6.57"}
    random = {source = "hashicorp/random",version = "~>3.7"}
  }
}
# Configures the provider connection and any region-specific alias used by this stack.
provider "aws" {
  region = var.aws_region
}
