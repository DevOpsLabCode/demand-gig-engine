# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the customer-managed KMS key and policy used by application data, logs, queues, and audit services.
# Reading guide: Each comment explains why the following Terraform block exists.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

# Build the KMS key policy that preserves account administration and grants only required AWS services cryptographic access.
data "aws_iam_policy_document" "this" {
  # Preserve full KMS key administration for the owning AWS account root principal.
  statement {
    sid       = "EnableAccountAdministration"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  # Allow CloudWatch Logs to use the key only through the regional Logs service and account-scoped encryption context.
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey*",
      "kms:ReEncrypt*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${data.aws_region.current.name}.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values = [
        "arn:${data.aws_partition.current.partition}:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"
      ]
    }
  }

  # Allow CloudTrail to generate data keys and describe the key for account-scoped trail encryption.
  statement {
    sid    = "AllowCloudTrailEncryption"
    effect = "Allow"
    actions = [
      "kms:DescribeKey",
      "kms:GenerateDataKey*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values = [
        "arn:${data.aws_partition.current.partition}:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${var.name}"
      ]
    }

    condition {
      test     = "StringLike"
      variable = "kms:EncryptionContext:aws:cloudtrail:arn"
      values = [
        "arn:${data.aws_partition.current.partition}:cloudtrail:*:${data.aws_caller_identity.current.account_id}:trail/*"
      ]
    }
  }
}

# Creates the customer-managed encryption key shared by protected services.
resource "aws_kms_key" "this" {
  description             = "${var.name} application encryption"
  enable_key_rotation     = true
  deletion_window_in_days = var.deletion_window
  policy                  = data.aws_iam_policy_document.this.json
  tags                    = var.tags
}

# Provides a stable, human-readable name for the KMS key.
resource "aws_kms_alias" "this" {
  name          = "alias/${var.name}"
  target_key_id = aws_kms_key.this.key_id
}
