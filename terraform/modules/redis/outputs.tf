
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

output "runtime_secret_arn" {
  description = "Secrets Manager ARN containing the authenticated REDIS_URL value."
  value       = aws_secretsmanager_secret.runtime.arn
  sensitive   = true
}
