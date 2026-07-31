# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes database endpoints, identifiers, and protected secret references.

output "endpoint" {
  description = "Direct RDS PostgreSQL writer endpoint, excluding the port."
  value       = aws_db_instance.this.address
}

output "proxy_endpoint" {
  description = "RDS Proxy endpoint used by ECS tasks to pool and protect PostgreSQL connections."
  value       = aws_db_proxy.this.endpoint
}

output "secret_arn" {
  description = "Secrets Manager ARN containing the database login used by RDS Proxy."
  value       = aws_secretsmanager_secret.db.arn
  sensitive   = true
}

output "db_arn" {
  description = "RDS database instance ARN used by AWS Backup."
  value       = aws_db_instance.this.arn
}

output "db_identifier" {
  description = "RDS identifier used by CloudWatch alarm dimensions."
  value       = aws_db_instance.this.identifier
}

output "runtime_secret_arn" {
  description = "Secrets Manager ARN containing DATABASE_URL and the Django SECRET_KEY."
  value       = aws_secretsmanager_secret.runtime.arn
  sensitive   = true
}
