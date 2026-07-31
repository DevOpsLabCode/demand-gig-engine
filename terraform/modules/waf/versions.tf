# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the AWS provider source required by this reusable child module.

terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}
