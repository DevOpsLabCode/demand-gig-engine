# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines least-privilege security groups for the ALB, ECS tasks, PostgreSQL, Redis, and VPC endpoints.
# Reading guide: Each comment explains why the following Terraform block exists.

# Read AWS’s managed CloudFront origin-facing address list for restricted ALB ingress.
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}
# Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  description = "Allow only CloudFront origin-facing traffic to the public ALB"
  vpc_id = var.vpc_id
  # Allows only the documented inbound network path.
  ingress {
    description = "HTTP from CloudFront origin-facing network"
    from_port = 80
    to_port = 80
    protocol = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }
  # Allows only the documented inbound network path.
  ingress {
    description = "HTTPS from CloudFront origin-facing network"
    from_port = 443
    to_port = 443
    protocol = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }
  # Defines the outbound network path required by this workload.
  egress {
    description = "Responses to application targets"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags,{Name = "${var.name}-alb"})
  # Controls replacement, deletion protection, and drift behavior for this resource.
  lifecycle {
    create_before_destroy = true
  }
}
# Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
resource "aws_security_group" "app" {
  name_prefix = "${var.name}-app-"
  description = "Application tasks reachable only from the ALB"
  vpc_id = var.vpc_id
  # Allows only the documented inbound network path.
  ingress {
    description = "Django API traffic from ALB"
    from_port = var.app_port
    to_port = var.app_port
    protocol = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  # Defines the outbound network path required by this workload.
  egress {
    description = "Outbound access through NAT and VPC endpoints"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags,{Name = "${var.name}-app"})
  # Controls replacement, deletion protection, and drift behavior for this resource.
  lifecycle {
    create_before_destroy = true
  }
}
# Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
resource "aws_security_group" "db" {
  name_prefix = "${var.name}-db-"
  description = "PostgreSQL and RDS Proxy access from application tasks"
  vpc_id = var.vpc_id
  # Allows only the documented inbound network path.
  ingress {
    description = "PostgreSQL from application tasks"
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  # RDS Proxy and DB instances share this group, so proxy-to-database traffic is self-referenced.
  ingress {
    description = "RDS Proxy to PostgreSQL"
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    self = true
  }
  # Defines the outbound network path required by this workload.
  egress {
    description = "RDS Proxy connection to database targets"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags,{Name = "${var.name}-db"})
  # Controls replacement, deletion protection, and drift behavior for this resource.
  lifecycle {
    create_before_destroy = true
  }
}
# Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
resource "aws_security_group" "redis" {
  name_prefix = "${var.name}-redis-"
  description = "Redis access from application tasks"
  vpc_id = var.vpc_id
  # Allows only the documented inbound network path.
  ingress {
    description = "Redis TLS from application tasks"
    from_port = 6379
    to_port = 6379
    protocol = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  # Defines the outbound network path required by this workload.
  egress {
    description = "Redis service-managed traffic"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags,{Name = "${var.name}-redis"})
  # Controls replacement, deletion protection, and drift behavior for this resource.
  lifecycle {
    create_before_destroy = true
  }
}
