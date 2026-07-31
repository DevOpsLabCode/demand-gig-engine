# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes deployment identifiers, endpoints, bucket names, role ARNs, and operational values from the root stack.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `cloudfront_url`: HTTPS URL assigned to the CloudFront distribution.
output "cloudfront_url" {
  value = "https://${module.cloudfront.domain_name}"
}
# Output `application_url`: Canonical public HTTPS application URL using the configured domain.
output "application_url" {
  value = local.application_url
}
# Output `ecr_repository_urls`: Map of application image names to ECR URLs used by build and deployment scripts.
output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}
# Output `github_actions_role_arn`: ARN of the environment image-and-service release role.
output "github_actions_role_arn" {
  description = "ARN of the environment image-and-service release role; Terraform plan/apply uses account-foundation roles."
  value       = module.github_oidc.role_arn
}
# Output `database_secret_arn`: ARN of the database secret resource consumed by this module.
output "database_secret_arn" {
  value     = module.database.secret_arn
  sensitive = true
}
# Output `provider_credentials_secret_arn`: ARN of the provider credentials secret resource consumed by this module.
output "provider_credentials_secret_arn" {
  value = module.secrets_manager.secret_arn
}
# Output `static_bucket_id`: Identifier of the static bucket resource consumed by this module.
output "static_bucket_id" {
  value = module.static.bucket_id
}
# Output `media_bucket_id`: Identifier of the media bucket resource consumed by this module.
output "media_bucket_id" {
  value = module.media.bucket_id
}
# Output `cloudfront_distribution_id`: CloudFront distribution ID used by deployment invalidations.
output "cloudfront_distribution_id" {
  value = module.cloudfront.distribution_id
}
# Output `ecs_cluster_arn`: ARN of the ecs cluster resource consumed by this module.
output "ecs_cluster_arn" {
  value = module.cluster.cluster_arn
}
# Output `backend_task_definition_arn`: ARN of the backend task definition resource consumed by this module.
output "backend_task_definition_arn" {
  value = module.backend.task_definition_arn
}
# Output `app_subnet_ids`: Private application subnet IDs used by ECS workloads.
output "app_subnet_ids" {
  value = module.networking.app_subnet_ids
}
# Output `app_security_group_id`: Security-group ID attached to the application workload.
output "app_security_group_id" {
  value = module.security.app_sg_id
}
# Output `backend_service_name`: ECS API service name used by deployment scripts to scale and inspect the workload.
output "backend_service_name" {
  value = module.backend.service_name
}

# Output `migration_task_definition_arn`: ARN of the migration task definition resource consumed by this module.
output "migration_task_definition_arn" {
  value = module.migration.task_definition_arn
}

# Output `migration_container_name`: Container name targeted by the one-off ECS database migration task.
output "migration_container_name" {
  value = module.migration.service_name
}
