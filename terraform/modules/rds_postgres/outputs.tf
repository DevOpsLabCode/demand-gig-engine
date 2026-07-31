output "endpoint" {
  value = aws_db_instance.this.address
}
output "proxy_endpoint" {
  value = aws_db_proxy.this.endpoint
}
output "secret_arn" {
  value = aws_secretsmanager_secret.db.arn
}
output "db_arn" {
  value = aws_db_instance.this.arn
}
output "runtime_secret_arn" {
  value = aws_secretsmanager_secret.runtime.arn
}

output "proxy_name" {
  value = aws_db_proxy.this.name
}
