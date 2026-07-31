# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Reuses the account-wide GitHub OIDC provider and creates a least-privilege deployment role without long-lived AWS access keys.
# Reading guide: Each comment explains why the following Terraform block exists.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

# Read the account-wide GitHub OIDC provider created by terraform/global/account.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# Construct exact GitHub OIDC subject patterns for approved branches, protected environments, and optional pull requests.
locals {
  cluster_name = element(reverse(split("/", var.cluster_arn)), 0)
  repository_subjects = concat(
    [for branch in var.allowed_branches : "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/${branch}"],
    var.allow_pull_requests ? ["repo:${var.github_org}/${var.github_repo}:pull_request"] : [],
    [for environment in var.allowed_environments : "repo:${var.github_org}/${var.github_repo}:environment:${environment}"],
  )
  service_arn = "arn:${data.aws_partition.current.partition}:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/${local.cluster_name}/*"
}

# Build the web-identity trust policy that limits role assumption to the approved GitHub repository subjects.
data "aws_iam_policy_document" "assume" {
  # Trust GitHub web identities only when audience and repository-subject conditions match the approved workflow contexts.
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.repository_subjects
    }
  }
}

# Creates an IAM role with a narrowly defined trust relationship.
resource "aws_iam_role" "github" {
  permissions_boundary = var.permissions_boundary_arn
  name                 = var.name
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  max_session_duration = 3600
  tags                 = var.tags
}

resource "aws_iam_role_policy" "github" {
  #checkov:skip=CKV_AWS_111:ecr:GetAuthorizationToken cannot be resource-scoped; all write operations use exact ECR repository or ECS service ARNs.
  #checkov:skip=CKV_AWS_356:AWS requires Resource "*" for ecr:GetAuthorizationToken and no other statement in this deployment policy uses a wildcard resource.
  role = aws_iam_role.github.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = var.ecr_arns
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:DescribeServices", "ecs:UpdateService"]
        Resource = local.service_arn
      },
    ]
  })
}
