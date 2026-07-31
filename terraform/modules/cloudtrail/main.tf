data "aws_caller_identity" "current" {
}
data "aws_partition" "current" {
}
data "aws_region" "current" {
}
locals {
  trail_arn = "arn:${data.aws_partition.current.partition}:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${var.name}"
}
resource "aws_s3_bucket" "logs" {
  bucket = "${var.name}-${data.aws_caller_identity.current.account_id}-cloudtrail"
  tags = var.tags
}
resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    id = "archive"
    status = "Enabled"
    filter {
    }
    transition {
      days = 90
      storage_class = "GLACIER_IR"
    }
    expiration {
      days = var.retention_days
    }
  }
}
data "aws_iam_policy_document" "logs" {
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
resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs.json
}
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
