# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes non-secret Redis identifiers and the ARN of the protected connection secret.

output "endpoint" {
  description = "Primary Redis endpoint; applications should normally consume runtime_secret_arn instead."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  description = "TLS Redis listener port."
  value       = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  description = "Replication-group ID used by CloudWatch alarm dimensions."
  value       = aws_elasticache_replication_group.this.replication_group_id
}

output "runtime_secret_arn" {
  description = "Secrets Manager ARN containing the authenticated REDIS_URL value."
  value       = aws_secretsmanager_secret.runtime.arn
  sensitive   = true

  # Do not expose the ARN to ECS until the JSON value has an AWSCURRENT version.
  depends_on = [
    aws_secretsmanager_secret_version.runtime,
  ]
}
