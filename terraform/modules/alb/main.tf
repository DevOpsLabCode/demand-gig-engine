
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the internet-facing Application Load Balancer, secure listeners, access logging, and backend target group.
# Reading guide: Each listener represents one deliberate origin-security mode.

resource "aws_lb" "this" {
  #checkov:skip=CKV2_AWS_28:The root stack attaches a dedicated REGIONAL Web ACL through aws_wafv2_web_acl_association; this reusable module cannot declare the cross-module association itself.
  #checkov:skip=CKV2_AWS_20:Custom-domain deployments create an HTTP-to-HTTPS redirect; no-domain deployments accept only CloudFront managed-prefix traffic because the AWS ALB hostname cannot receive an ACM certificate.
  name                       = substr(var.name, 0, 32)
  load_balancer_type         = "application"
  subnets                    = var.subnet_ids
  security_groups            = var.security_group_ids
  drop_invalid_header_fields = true
  desync_mitigation_mode     = "strictest"
  enable_deletion_protection = var.deletion_protection
  idle_timeout               = 60

  access_logs {
    bucket  = var.access_log_bucket_id
    prefix  = var.access_log_prefix
    enabled = true
  }

  tags = var.tags
}

resource "aws_lb_target_group" "backend" {
  #checkov:skip=CKV_AWS_378:ALB-to-ECS traffic remains inside private VPC subnets and security groups; viewer and CloudFront-origin traffic is encrypted before reaching this internal hop.
  name        = substr("${var.name}-api", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/health/"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
  tags                 = var.tags
}

# Redirect clear-text origin requests to TLS whenever a custom origin certificate exists.
resource "aws_lb_listener" "http_redirect" {
  count             = var.certificate_arn == null ? 0 : 1
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "http_cloudfront_origin" {
  #checkov:skip=CKV_AWS_2:No-domain mode is CloudFront-only, viewer HTTPS is enforced, and ALB ingress is restricted to the AWS CloudFront managed prefix list.
  #checkov:skip=CKV_AWS_103:This conditional HTTP listener exists only when no ACM origin certificate can be issued for the AWS-generated ALB hostname; requests still require the CloudFront-only origin-verification header.
  count             = var.certificate_arn == null ? 1 : 0
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "http_cloudfront_origin" {
  count        = var.certificate_arn == null ? 1 : 0
  listener_arn = aws_lb_listener.http_cloudfront_origin[0].arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    http_header {
      http_header_name = "X-Origin-Verify"
      values           = [var.origin_verify_header_value]
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = var.certificate_arn == null ? 0 : 1
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "https_cloudfront_origin" {
  count        = var.certificate_arn == null ? 0 : 1
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    http_header {
      http_header_name = "X-Origin-Verify"
      values           = [var.origin_verify_header_value]
    }
  }
}
