# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the internet-facing Application Load Balancer, HTTPS listener, access logging, and backend target group.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws lb resource owned by this file.
resource "aws_lb" "this" {
  name = substr(var.name,0,32)
  load_balancer_type = "application"
  subnets = var.subnet_ids
  security_groups = var.security_group_ids
  drop_invalid_header_fields = true
  enable_deletion_protection = var.deletion_protection
  idle_timeout = 60
  tags = var.tags
}
# Defines backend health checks and the ECS destination for load-balanced requests.
resource "aws_lb_target_group" "backend" {
  name = substr("${var.name}-api",0,32)
  port = 8000
  protocol = "HTTP"
  vpc_id = var.vpc_id
  target_type = "ip"
  # Defines how the service determines whether a target is healthy.
  health_check {
    path = "/api/health/"
    matcher = "200"
    interval = 30
    timeout = 5
    healthy_threshold = 2
    unhealthy_threshold = 3
  }
  deregistration_delay = 30
  tags = var.tags
}
# Accepts HTTP or HTTPS traffic and forwards or redirects it according to the listener policy.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port = 80
  protocol = "HTTP"
  # Generates repeated nested configuration from the supplied collection.
  dynamic "default_action" {
    for_each = var.certificate_arn == null ? [1] :[]
    # Defines the nested block emitted for each item in the dynamic collection.
    content {
      type = "forward"
      target_group_arn = aws_lb_target_group.backend.arn
    }
  }
  # Generates repeated nested configuration from the supplied collection.
  dynamic "default_action" {
    for_each = var.certificate_arn != null ? [1] :[]
    # Defines the nested block emitted for each item in the dynamic collection.
    content {
      type = "redirect"
      redirect {
        port = "443"
        protocol = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}
# Accepts HTTP or HTTPS traffic and forwards or redirects it according to the listener policy.
resource "aws_lb_listener" "https" {
  count = var.certificate_arn == null ? 0 :1
  load_balancer_arn = aws_lb.this.arn
  port = 443
  protocol = "HTTPS"
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn = var.certificate_arn
  # Specifies the action used when no more-specific WAF rule matches.
  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
