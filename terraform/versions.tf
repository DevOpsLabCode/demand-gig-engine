# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Pins Terraform and provider compatibility ranges to keep deployments reproducible.
# Reading guide: Each comment explains why the following Terraform block exists.

# Define Terraform and provider compatibility before any resources are evaluated.
terraform {
  backend "s3" {
  }
  required_version = ">= 1.10.0"
  required_providers {
    aws = {source = "hashicorp/aws",version = "~> 6.57"}
    random = {source = "hashicorp/random",version = "~> 3.7"}
    tls = {source = "hashicorp/tls",version = "~> 4.1"}
  }
}
