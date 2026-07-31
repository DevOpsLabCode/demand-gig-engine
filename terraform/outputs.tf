output "cloudfront_url" {
  value = "https://${module.cloudfront.domain_name}"
}
output "application_url" {
  value = local.application_url
}
output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}
output "github_actions_role_arn" {
  value = module.github_oidc.role_arn
}
output "database_secret_arn" {
  value = module.database.secret_arn
  sensitive = true
}
output "provider_credentials_secret_arn" {
  value = module.secrets_manager.secret_arn
}
output "static_bucket_id" {
  value = module.static.bucket_id
}
output "media_bucket_id" {
  value = module.media.bucket_id
}
output "cloudfront_distribution_id" {
  value = module.cloudfront.distribution_id
}
output "ecs_cluster_arn" {
  value = module.cluster.cluster_arn
}
output "backend_task_definition_arn" {
  value = module.backend.task_definition_arn
}
output "app_subnet_ids" {
  value = module.networking.app_subnet_ids
}
output "app_security_group_id" {
  value = module.security.app_sg_id
}
output "backend_service_name" {
  value = module.backend.service_name
}

output "migration_task_definition_arn" {
  value = module.migration.task_definition_arn
}

output "migration_container_name" {
  value = module.migration.service_name
}

output "database_proxy_name" {
  value = module.database.proxy_name
}
