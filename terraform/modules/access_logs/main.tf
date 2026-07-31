
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the dedicated S3 destination used by ALB, CloudFront, and source-bucket access logging.
# Reading guide: The bucket is deliberately isolated from application data and retains immutable historical log versions.

# Read the active AWS account so the ALB delivery policy can be scoped to this account only.
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# Read the bucket owner canonical ID so the explicit ACL preserves full owner control.
data "aws_canonical_user_id" "current" {}

# AWS documents this canonical user ID for CloudFront legacy standard-log delivery.
# Keeping it explicit prevents a later Terraform apply from replacing CloudFront's required grant with a canned private ACL.
locals {
  cloudfront_log_delivery_canonical_user_id = "c4c1ede66af53448b93c283ce9448c4ba468c9432aa01d700d3878632f77d2d0"
}

resource "aws_s3_bucket" "this" {
  #checkov:skip=CKV_AWS_18:A dedicated terminal log sink cannot log to itself without recursively generating new access-log objects.
  #checkov:skip=CKV_AWS_144:Cross-region replication is delegated to the organization backup and disaster-recovery policy and destination account.
  #checkov:skip=CKV2_AWS_62:Security analytics reads the centralized prefixes directly; per-object event notifications are not part of the control design.
  #checkov:skip=CKV_AWS_145:ALB and legacy CloudFront standard-log delivery require S3-managed encryption compatibility; application and audit data use customer-managed KMS keys.
  bucket        = var.name
  force_destroy = var.force_destroy
  tags          = var.tags
}

# Keep ACL support enabled because CloudFront standard logging uses the S3 log-delivery canonical user.
resource "aws_s3_bucket_ownership_controls" "this" {
  #checkov:skip=CKV2_AWS_65:CloudFront legacy standard logging requires the documented log-delivery canonical-user ACL; public ACLs remain fully blocked.
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Preserve bucket-owner control and grant CloudFront's documented log-delivery
# canonical user FULL_CONTROL. A canned "private" ACL would remove this grant on
# a later Terraform apply and silently stop CloudFront access-log delivery.
resource "aws_s3_bucket_acl" "this" {
  depends_on = [aws_s3_bucket_ownership_controls.this]
  bucket     = aws_s3_bucket.this.id

  access_control_policy {
    grant {
      grantee {
        id   = data.aws_canonical_user_id.current.id
        type = "CanonicalUser"
      }
      permission = "FULL_CONTROL"
    }

    grant {
      grantee {
        id   = local.cloudfront_log_delivery_canonical_user_id
        type = "CanonicalUser"
      }
      permission = "FULL_CONTROL"
    }

    owner {
      id = data.aws_canonical_user_id.current.id
    }
  }
}

# Reject all public ACL and bucket-policy exposure.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Preserve previous log-object versions for investigation and recovery.
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt every delivered log object at rest with Amazon S3 managed keys.
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Abort abandoned uploads and transition/expire old logs according to the retention policy.
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "centralized-access-log-retention"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = var.retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }
  }
}

# Permit ALB log delivery to the account-scoped prefix and deny every non-TLS S3 request.
data "aws_iam_policy_document" "this" {
  statement {
    sid       = "AllowALBLogDelivery"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this.arn}/${var.alb_prefix}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]

    principals {
      type        = "Service"
      identifiers = ["logdelivery.elasticloadbalancing.amazonaws.com"]
    }
  }

  statement {
    sid       = "AllowS3ServerAccessLogDelivery"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this.arn}/s3/*"]

    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:s3:::*"]
    }
  }

  statement {
    sid       = "AllowALBLogDeliveryAclCheck"
    effect    = "Allow"
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.this.arn]

    principals {
      type        = "Service"
      identifiers = ["logdelivery.elasticloadbalancing.amazonaws.com"]
    }
  }

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.this.arn, "${aws_s3_bucket.this.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.this.json
}
