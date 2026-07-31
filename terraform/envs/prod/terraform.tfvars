# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Environment: prod
# Purpose: Supplies documented environment values for the Terraform root stack.

environment               = "prod"
aws_region                = "us-east-1"
vpc_cidr                  = "10.10.0.0/16"
az_count                  = 3
nat_gateway_per_az        = true
backend_image             = "REPLACED_BY_DEPLOY_SCRIPT"
backend_cpu               = 1024
backend_memory            = 2048
backend_desired_count     = 2
worker_cpu                = 512
worker_memory             = 1024
worker_desired_count      = 2
db_instance_class         = "db.r7g.large"
db_allocated_storage      = 100
db_multi_az               = true
redis_node_type           = "cache.r7g.large"
redis_replicas            = 2
deletion_protection       = true
schedule_enabled          = true
enable_guardduty          = true
payment_provider          = "fake"
cloudfront_price_class    = "PriceClass_100"
cloudtrail_retention_days = 2555
create_dns                = false
domain_name               = ""
hosted_zone_id            = ""
alarm_email               = ""
ses_identity_arn          = null
tags = {
  Owner      = "DevOpsLabCode"
  CostCenter = "DemandGig"
}

# Production recovery points become immutable after the three-day grace period.
enable_backup_vault_lock          = true
backup_retention_days             = 365
backup_max_retention_days         = 3650
backup_cold_storage_after_days    = 90
backup_vault_lock_changeable_days = 3

# Keep enabled: production must not deploy with fake payments, missing alarms, or no custom TLS domain.
enforce_production_readiness = true
viewer_certificate_arn       = null
origin_certificate_arn       = null
