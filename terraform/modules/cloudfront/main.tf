# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the CloudFront distribution, origin access control, SPA routing function, WAF association, and least-privilege S3 policy.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws cloudfront origin access control resource owned by this file.
resource "aws_cloudfront_origin_access_control" "this" {
  name = var.name
  origin_access_control_origin_type = "s3"
  signing_behavior = "always"
  signing_protocol = "sigv4"
}
# Runs lightweight request-rewrite logic at CloudFront edge locations.
resource "aws_cloudfront_function" "spa_rewrite" {
  name = "${var.name}-spa-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite extensionless frontend routes to the React application shell"
  publish = true
  code = file("${path.module}/spa-rewrite.js")
}
# Adds browser security and caching headers to CloudFront responses.
resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${var.name}-security-headers"
  security_headers_config {
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override = true
    }
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains = true
      preload = true
      override = true
    }
    xss_protection {
      mode_block = true
      protection = true
      override = true
    }
  }
}
# Creates the global content-delivery layer for the frontend and API origin.
resource "aws_cloudfront_distribution" "this" {
  enabled = true
  is_ipv6_enabled = true
  default_root_object = "index.html"
  http_version = "http2and3"
  price_class = var.price_class
  aliases = var.domain_name == "" ? [] :[var.domain_name]
  web_acl_id = var.web_acl_arn
  # Defines a backend from which CloudFront retrieves content.
  origin {
    domain_name = var.bucket_domain_name
    origin_id = "s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }
  # Defines a backend from which CloudFront retrieves content.
  origin {
    domain_name = var.alb_domain_name
    origin_id = "alb"

    custom_header {
      name  = "X-Forwarded-Viewer-Proto"
      value = "https"
    }

    custom_origin_config {
      http_port = 80
      https_port = 443
      origin_protocol_policy = var.use_https_origin ? "https-only" :"http-only"
      origin_ssl_protocols = ["TLSv1.2"]
      origin_read_timeout = 60
      origin_keepalive_timeout = 5
    }
  }
  # Defines routing, protocol, and cache behavior for the default CloudFront path.
  default_cache_behavior {
    target_origin_id = "s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods = ["GET","HEAD","OPTIONS"]
    cached_methods = ["GET","HEAD"]
    compress = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    function_association {
      event_type = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }
  # Generates repeated nested configuration from the supplied collection.
  dynamic "ordered_cache_behavior" {
    for_each = toset(["/api*","/accounts*","/admin*"])
    # Defines the nested block emitted for each item in the dynamic collection.
    content {
      path_pattern = ordered_cache_behavior.value
      target_origin_id = "alb"
      viewer_protocol_policy = "redirect-to-https"
      allowed_methods = ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"]
      cached_methods = ["GET","HEAD"]
      compress = true
      response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
      forwarded_values {
        query_string = true
        headers = ["*"]
        cookies {
          forward = "all"
        }
      }
      min_ttl = 0
      default_ttl = 0
      max_ttl = 0
    }
  }
  # Defines routing and caching for a more-specific CloudFront path pattern.
  ordered_cache_behavior {
    path_pattern = "/share*"
    target_origin_id = "alb"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods = ["GET","HEAD","OPTIONS"]
    cached_methods = ["GET","HEAD"]
    compress = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    forwarded_values {
      query_string = true
      headers = ["Host"]
      cookies {
        forward = "none"
      }
    }
    min_ttl = 0
    default_ttl = 60
    max_ttl = 300
  }
  # Applies optional geographic delivery restrictions.
  restrictions {
    # Defines the geographic allow or deny policy.
    geo_restriction {
      restriction_type = "none"
    }
  }
  # Selects the TLS certificate and minimum security policy exposed to viewers.
  viewer_certificate {
    acm_certificate_arn = var.certificate_arn
    cloudfront_default_certificate = var.certificate_arn == null
    ssl_support_method = var.certificate_arn == null ? null :"sni-only"
    minimum_protocol_version = var.certificate_arn == null ? "TLSv1" :"TLSv1.2_2021"
  }
  tags = var.tags
}
# Build the S3 bucket policy that grants read access only to this CloudFront distribution and denies non-TLS requests.
data "aws_iam_policy_document" "bucket" {
  # Allow object reads only from the specific CloudFront distribution through Origin Access Control.
  statement {
    sid = "AllowCloudFrontRead"
    actions = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/*"]
    principals {
      type = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test = "StringEquals"
      variable = "AWS:SourceArn"
      values = [aws_cloudfront_distribution.this.arn]
    }
  }
  # Deny every S3 action when the request is not protected by TLS.
  statement {
    sid = "DenyInsecureTransport"
    effect = "Deny"
    actions = ["s3:*"]
    resources = [var.bucket_arn,"${var.bucket_arn}/*"]
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
resource "aws_s3_bucket_policy" "this" {
  bucket = var.bucket_id
  policy = data.aws_iam_policy_document.bucket.json
}
