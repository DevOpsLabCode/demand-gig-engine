
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines least-privilege security groups for the ALB, ECS tasks, PostgreSQL, and Redis.
# Reading guide: Ingress identifies who may initiate a connection; egress limits each tier to the ports it actually uses.

# Read AWS's managed CloudFront origin-facing address list so the public ALB
# cannot be reached directly from arbitrary internet addresses.
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  description = "Allow only CloudFront origin-facing traffic to the public ALB"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from CloudFront origin-facing network"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  ingress {
    description     = "HTTPS from CloudFront origin-facing network"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  # The ALB initiates only application-port connections to targets inside this VPC.
  egress {
    description = "Application-port traffic to private ECS targets"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(var.tags, { Name = "${var.name}-alb" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "app" {
  name_prefix = "${var.name}-app-"
  description = "Application tasks reachable only from the ALB"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Django API traffic from ALB"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # External provider APIs, AWS public endpoints, and package-independent HTTPS calls.
  egress {
    description = "HTTPS to approved internet and AWS service endpoints through NAT"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "PostgreSQL through RDS Proxy in private database subnets"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Encrypted Redis traffic in private database subnets"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Route 53 Resolver is reached inside the VPC; both transports are allowed
  # because DNS can fall back from UDP to TCP for larger responses.
  egress {
    description = "DNS over UDP to the VPC resolver"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "DNS over TCP to the VPC resolver"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(var.tags, { Name = "${var.name}-app" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "db" {
  name_prefix = "${var.name}-db-"
  description = "PostgreSQL and RDS Proxy access from application tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from application tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  # RDS Proxy and the database share this group, so proxy-to-database traffic
  # must be permitted between members of the same security group.
  ingress {
    description = "RDS Proxy to PostgreSQL"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "RDS Proxy connection to PostgreSQL targets inside the VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(var.tags, { Name = "${var.name}-db" })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.name}-redis-"
  description = "Redis access from application tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis TLS from application tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description = "Redis node traffic inside the private VPC"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(var.tags, { Name = "${var.name}-redis" })

  lifecycle {
    create_before_destroy = true
  }
}
