# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates an encrypted, access-logged S3 audit bucket and a multi-region CloudTrail with integrity validation.
# Reading guide: Each comment explains why the following Terraform block exists.

# Read the active AWS account identity for policies, names, and ownership checks.
data "aws_caller_identity" "current" {
}
# Read the AWS partition so service principals and ARNs work in commercial, GovCloud, or China partitions.
data "aws_partition" "current" {
}
# Read the current region for KMS encryption-context restrictions and trail configuration.
data "aws_region" "current" {
}
# Build partition-aware CloudTrail and account principals used by the encrypted audit-bucket policy.
locals {
  trail_arn = "arn:${data.aws_partition.current.partition}:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${var.name}"
}
# Creates an encrypted object-storage bucket for static assets, media, logs, or state.
resource "aws_s3_bucket" "logs" {
  bucket = "${var.name}-${data.aws_caller_identity.current.account_id}-cloudtrail"
  tags = var.tags
}
# Makes bucket ownership deterministic and disables legacy ACL ownership ambiguity.
resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id
  # Defines one ordered policy or lifecycle rule.
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
# Prevents accidental public exposure through S3 ACLs or policies.
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
# Retains prior object versions to support recovery and auditability.
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  # Enables or suspends object versioning.
  versioning_configuration {
    status = "Enabled"
  }
}
# Enforces server-side encryption for newly written objects.
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  # Defines one ordered policy or lifecycle rule.
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}
# Transitions or expires objects according to retention and cost policies.
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  # Defines one ordered policy or lifecycle rule.
  rule {
    id = "archive"
    status = "Enabled"
    filter {
    }
    # Moves retained data to a lower-cost storage class after the configured age.
    transition {
      days = 90
      storage_class = "GLACIER_IR"
    }
    # Removes data after its documented retention period.
    expiration {
      days = var.retention_days
    }
  }
}
# Build the S3 bucket policy that permits CloudTrail delivery while denying insecure transport.
data "aws_iam_policy_document" "logs" {
  # Permit CloudTrail to verify bucket ownership and ACL state before delivering audit logs.
  statement {
    sid = "AWSCloudTrailAclCheck"
    actions = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.logs.arn]
    principals {
      type = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    condition {
      test = "StringEquals"
      variable = "aws:SourceArn"
      values = [local.trail_arn]
    }
  }
  # Permit CloudTrail to write account-scoped log objects only when it retains bucket-owner control.
  statement {
    sid = "AWSCloudTrailWrite"
    actions = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.logs.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]
    principals {
      type = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    condition {
      test = "StringEquals"
      variable = "s3:x-amz-acl"
      values = ["bucket-owner-full-control"]
    }
    condition {
      test = "StringEquals"
      variable = "aws:SourceArn"
      values = [local.trail_arn]
    }
  }
  # Deny every S3 action when the request is not protected by TLS.
  statement {
    sid = "DenyInsecureTransport"
    effect = "Deny"
    actions = ["s3:*"]
    resources = [aws_s3_bucket.logs.arn,"${aws_s3_bucket.logs.arn}/*"]
    principals {
      type = "AWS"
      identifiers = ["*"]
    }
    condition {
      test = "Bool"
      variable = "aws:SecureTransport"
      values = ["false"]
    }
  }
}
# Applies resource-level access controls and transport requirements to the bucket.
resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs.json
}
# Records AWS API activity for audit, investigation, and governance.
resource "aws_cloudtrail" "this" {
  name = var.name
  s3_bucket_name = aws_s3_bucket.logs.id
  kms_key_id = var.kms_key_arn
  include_global_service_events = true
  is_multi_region_trail = true
  enable_log_file_validation = true
  depends_on = [aws_s3_bucket_policy.logs]
  tags = var.tags
}
