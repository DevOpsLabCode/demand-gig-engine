# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates an encrypted, subnet-isolated Redis replication group with automatic failover when replicas are enabled.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws elasticache subnet group resource owned by this file.
resource "aws_elasticache_subnet_group" "this" {
  name = var.name
  subnet_ids = var.subnet_ids
}
# Creates encrypted Redis primary and replica nodes with failover support.
resource "aws_elasticache_replication_group" "this" {
  replication_group_id = var.name
  description = var.name
  engine = "redis"
  engine_version = "7.1"
  node_type = var.node_type
  num_cache_clusters = var.replicas + 1
  automatic_failover_enabled = var.replicas > 0
  multi_az_enabled = var.replicas > 0
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id = var.kms_key_arn
  subnet_group_name = aws_elasticache_subnet_group.this.name
  security_group_ids = var.security_group_ids
  snapshot_retention_limit = 7
  apply_immediately = false
  tags = var.tags
}
