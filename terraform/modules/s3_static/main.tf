# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the private, versioned, KMS-encrypted bucket used for frontend assets or application object storage.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws s3 bucket resource owned by this file.
resource "aws_s3_bucket" "this" {
  bucket        = var.name
  force_destroy = var.force_destroy
  tags          = var.tags
}

# Makes bucket ownership deterministic and disables legacy ACL ownership ambiguity.
resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id
  # Defines one ordered policy or lifecycle rule.
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Prevents accidental public exposure through S3 ACLs or policies.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Retains prior object versions to support recovery and auditability.
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  # Enables or suspends object versioning.
  versioning_configuration {
    status = "Enabled"
  }
}

# Enforces server-side encryption for newly written objects.
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  # Defines one ordered policy or lifecycle rule.
  rule {
    bucket_key_enabled = var.kms_key_arn != null
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn == null ? "AES256" : "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

# Transitions or expires objects according to retention and cost policies.
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  # Defines one ordered policy or lifecycle rule.
  rule {
    id     = "noncurrent"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }
  }
}

# Build the bucket policy that denies every request made without TLS.
data "aws_iam_policy_document" "tls" {
  count = var.create_tls_policy ? 1 : 0

  # Deny every S3 action when the request is not protected by TLS.
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

# Applies resource-level access controls and transport requirements to the bucket.
resource "aws_s3_bucket_policy" "tls" {
  count  = var.create_tls_policy ? 1 : 0
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.tls[0].json
}
