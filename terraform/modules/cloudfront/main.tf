
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates CloudFront delivery, private S3 access, secure response headers, WAF association, and access logging.
# Reading guide: Static frontend paths use the private S3 origin; dynamic application paths use the ALB origin.

resource "aws_cloudfront_origin_access_control" "this" {
  name                              = var.name
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "${var.name}-spa-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite extensionless frontend routes to the React application shell"
  publish = true
  code    = file("${path.module}/spa-rewrite.js")
}

resource "aws_cloudfront_function" "true_client_ip" {
  name    = "${var.name}-true-client-ip"
  runtime = "cloudfront-js-2.0"
  comment = "Overwrite the private origin viewer-IP header with CloudFront's authenticated client address"
  publish = true
  code    = file("${path.module}/true-client-ip.js")
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${var.name}-security-headers"

  security_headers_config {
    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    xss_protection {
      mode_block = true
      protection = true
      override   = true
    }
  }
}

# API requests are never cached, but required application headers, cookies, and
# query strings still reach the ALB. Keeping Host out of this policy lets
# CloudFront use the configured origin hostname for TLS SNI and validation.
resource "aws_cloudfront_cache_policy" "api_disabled" {
  name        = "${var.name}-api-disabled"
  comment     = "Disable caching for authenticated and state-changing application routes"
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_origin_request_policy" "api" {
  name    = "${var.name}-api-origin"
  comment = "Forward application inputs without forwarding the viewer Host header"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "whitelist"

    headers {
      items = [
        "Accept",
        "Accept-Language",
        "Access-Control-Request-Headers",
        "Access-Control-Request-Method",
        "Authorization",
        "Content-Type",
        "Origin",
        "Referer",
        "X-CSRFToken",
        "X-Origin-Viewer-IP",
        "X-Requested-With",
      ]
    }
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

# Public share pages use a short cache window. Viewer-IP metadata is forwarded
# only to the origin and deliberately excluded from the cache key, preserving
# cache efficiency while regional WAF still receives the authenticated address.
resource "aws_cloudfront_cache_policy" "share" {
  name        = "${var.name}-share"
  comment     = "Short-lived cache for public share pages"
  default_ttl = 60
  max_ttl     = 300
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

resource "aws_cloudfront_origin_request_policy" "share" {
  name    = "${var.name}-share-origin"
  comment = "Forward language and authenticated viewer IP without varying cache objects by IP"

  cookies_config {
    cookie_behavior = "none"
  }

  headers_config {
    header_behavior = "whitelist"

    headers {
      items = ["Accept-Language", "X-Origin-Viewer-IP"]
    }
  }

  query_strings_config {
    # Query strings already reach the origin through the share cache policy.
    query_string_behavior = "none"
  }
}

resource "aws_cloudfront_distribution" "this" {
  #checkov:skip=CKV_AWS_310:Origin failover requires an independently deployed secondary API stack and is implemented by the multi-region disaster-recovery layer rather than this single-region module.
  #checkov:skip=CKV_AWS_374:Worldwide delivery is a documented product requirement; geographic blocking would prevent legitimate global fans and organizers from accessing campaigns.
  #checkov:skip=CKV_AWS_174:The managed CloudFront certificate controls its own protocol policy; custom-domain deployments explicitly enforce TLSv1.2_2021.
  #checkov:skip=CKV2_AWS_47:The attached Web ACL includes AWSManagedRulesKnownBadInputsRuleSet, which contains the AWS-managed Log4j protections; the cross-module association is not resolved by this graph check.
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  http_version        = "http2and3"
  price_class         = var.price_class
  aliases             = var.domain_name == "" ? [] : [var.domain_name]
  web_acl_id = var.web_acl_arn

  logging_config {
    bucket          = var.access_log_bucket_domain_name
    include_cookies = false
    prefix          = "cloudfront/"
  }

  origin {
    domain_name              = var.bucket_domain_name
    origin_id                = "s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }

  origin {
    domain_name = var.alb_domain_name
    origin_id   = "alb"

    custom_header {
      name  = "X-Forwarded-Viewer-Proto"
      value = "https"
    }

    # This secret header is never exposed to viewers; ALB listener rules reject
    # requests that do not originate from this configured distribution.
    custom_header {
      name  = "X-Origin-Verify"
      value = var.origin_verify_header_value
    }

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = var.use_https_origin ? "https-only" : "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 5
    }
  }

  default_cache_behavior {
    target_origin_id           = "s3"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = toset(["/api*", "/accounts*", "/admin*"])

    content {
      path_pattern               = ordered_cache_behavior.value
      target_origin_id           = "alb"
      viewer_protocol_policy     = "redirect-to-https"
      allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods             = ["GET", "HEAD"]
      compress                   = true
      response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

      function_association {
        event_type   = "viewer-request"
        function_arn = aws_cloudfront_function.true_client_ip.arn
      }

      cache_policy_id          = aws_cloudfront_cache_policy.api_disabled.id
      origin_request_policy_id = aws_cloudfront_origin_request_policy.api.id
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/share*"
    target_origin_id           = "alb"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.true_client_ip.arn
    }

    cache_policy_id          = aws_cloudfront_cache_policy.share.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.share.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.certificate_arn
    cloudfront_default_certificate = var.certificate_arn == null
    ssl_support_method             = var.certificate_arn == null ? null : "sni-only"
    minimum_protocol_version       = var.certificate_arn == null ? "TLSv1" : "TLSv1.2_2021"
  }

  tags = var.tags
}

data "aws_iam_policy_document" "bucket" {
  statement {
    sid       = "AllowCloudFrontRead"
    actions   = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [var.bucket_arn, "${var.bucket_arn}/*"]

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
  bucket = var.bucket_id
  policy = data.aws_iam_policy_document.bucket.json
}
