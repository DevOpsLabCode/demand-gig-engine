
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the internet-facing Application Load Balancer, secure listeners, access logging, and backend target group.
# Reading guide: Each listener represents one deliberate origin-security mode.

resource "aws_lb" "this" {
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

# The AWS-generated ALB hostname cannot receive an ACM certificate. In no-domain
# development mode this listener accepts only CloudFront origin-facing traffic;
# end users still connect to CloudFront through HTTPS.
#checkov:skip=CKV_AWS_2:No-domain mode is CloudFront-only, viewer HTTPS is enforced, and ALB ingress is restricted to the AWS CloudFront managed prefix list.
resource "aws_lb_listener" "http_cloudfront_origin" {
  count             = var.certificate_arn == null ? 1 : 0
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
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
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
