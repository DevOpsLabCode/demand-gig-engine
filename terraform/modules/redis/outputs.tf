# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the redis Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `endpoint`: Primary Redis endpoint used by the application cache configuration.
output "endpoint" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}
# Output `port`: Redis listener port exposed by the replication group.
output "port" {
  value = aws_elasticache_replication_group.this.port
}
