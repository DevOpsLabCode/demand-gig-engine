# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the rds postgres Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `endpoint`: Direct RDS PostgreSQL writer endpoint, excluding the port.
output "endpoint" {
  value = aws_db_instance.this.address
}
# Output `proxy_endpoint`: RDS Proxy endpoint used by ECS tasks to pool and protect PostgreSQL connections.
output "proxy_endpoint" {
  value = aws_db_proxy.this.endpoint
}
# Output `secret_arn`: ARN of the secret resource consumed by this module.
output "secret_arn" {
  value = aws_secretsmanager_secret.db.arn
}
# Output `db_arn`: ARN of the db resource consumed by this module.
output "db_arn" {
  value = aws_db_instance.this.arn
}
# Output `runtime_secret_arn`: ARN of the runtime secret resource consumed by this module.
output "runtime_secret_arn" {
  value = aws_secretsmanager_secret.runtime.arn
}
