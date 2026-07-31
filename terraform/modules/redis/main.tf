
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates authenticated, encrypted, subnet-isolated Redis with failover and a protected runtime connection secret.

resource "aws_elasticache_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

# ElastiCache authentication tokens must be supplied by clients in addition to
# transport encryption. Alphanumeric generation avoids URL-encoding ambiguity.
resource "random_password" "auth" {
  length  = 64
  special = false
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = var.name
  description                = var.name
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.node_type
  num_cache_clusters         = var.replicas + 1
  automatic_failover_enabled = var.replicas > 0
  multi_az_enabled           = var.replicas > 0
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.auth.result
  auth_token_update_strategy = "ROTATE"
  kms_key_id                 = var.kms_key_arn
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = var.security_group_ids
  snapshot_retention_limit   = 7
  snapshot_window            = "04:00-05:00"
  maintenance_window         = "sun:05:30-sun:06:30"
  auto_minor_version_upgrade = true
  apply_immediately          = false
  tags                       = var.tags
}

# Rotation must update both ElastiCache and the URL consumed by ECS. The runbook
# uses auth_token_update_strategy=ROTATE before promoting the new secret value.
#checkov:skip=CKV2_AWS_57:Redis credential rotation is coordinated with ElastiCache token rotation and ECS deployment, not an independent rotation Lambda.
resource "aws_secretsmanager_secret" "runtime" {
  name                    = "${var.name}/redis"
  description             = "Authenticated TLS Redis URL consumed by ECS tasks"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 7
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id = aws_secretsmanager_secret.runtime.id
  secret_string = jsonencode({
    REDIS_URL = "rediss://:${random_password.auth.result}@${aws_elasticache_replication_group.this.primary_endpoint_address}:${aws_elasticache_replication_group.this.port}/0"
  })
}
