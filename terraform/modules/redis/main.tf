# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates authenticated, encrypted, subnet-isolated Redis with mandatory Multi-AZ automatic failover and a protected runtime connection secret.

locals {
  redis_port = 6379
}

resource "aws_elasticache_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

# ElastiCache authentication tokens must be supplied by clients in addition to
# transport encryption. Alphanumeric generation avoids URL-encoding ambiguity.
resource "random_password" "auth" {
  length  = 64
  special = false
}

# Pre-create encrypted destinations for engine diagnostics and slow commands.
resource "aws_cloudwatch_log_group" "engine" {
  name              = "/aws/elasticache/${var.name}/engine"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "slow" {
  name              = "/aws/elasticache/${var.name}/slow-log"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = var.name
  description                = var.name
  engine                     = "redis"
  engine_version             = var.engine_version
  node_type                  = var.node_type
  port                       = local.redis_port
  num_cache_clusters         = var.replicas + 1
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.auth.result
  auth_token_update_strategy = "ROTATE"
  kms_key_id                 = var.kms_key_arn
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = var.security_group_ids
  snapshot_retention_limit   = var.snapshot_retention_days
  snapshot_window            = "04:00-05:00"
  maintenance_window         = "sun:05:30-sun:06:30"
  auto_minor_version_upgrade = true
  apply_immediately          = var.apply_immediately

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.engine.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  tags = var.tags

  depends_on = [
    aws_cloudwatch_log_group.engine,
    aws_cloudwatch_log_group.slow,
  ]
}

resource "aws_secretsmanager_secret" "runtime" {
  #checkov:skip=CKV2_AWS_57:Redis credential rotation must coordinate ElastiCache ROTATE token staging with ECS deployment, so it is controlled by the documented runbook rather than an independent Lambda.
  name                    = "${var.name}/redis"
  description             = "Authenticated TLS Redis URL consumed by ECS tasks"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 7
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id = aws_secretsmanager_secret.runtime.id

  secret_string = jsonencode({
    REDIS_URL = "rediss://:${random_password.auth.result}@${aws_elasticache_replication_group.this.primary_endpoint_address}:${local.redis_port}/0"
  })
}
