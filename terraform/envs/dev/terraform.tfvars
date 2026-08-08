# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Environment: dev
# Purpose: Supplies documented environment values for the Terraform root stack.

environment               = "dev"
aws_region                = "us-east-1"
vpc_cidr                  = "10.20.0.0/16"
az_count                  = 2
nat_gateway_per_az        = false
backend_image             = "REPLACED_BY_DEPLOY_SCRIPT"
backend_cpu               = 512
backend_memory            = 1024
backend_desired_count     = 1
worker_cpu                = 256
worker_memory             = 512
worker_desired_count      = 1
db_instance_class         = "db.t4g.micro"
db_allocated_storage      = 20
db_multi_az               = false
redis_node_type           = "cache.t4g.micro"
redis_replicas            = 1
deletion_protection       = false
schedule_enabled          = true
enable_guardduty          = true
payment_provider          = "fake"
cloudfront_price_class    = "PriceClass_100"
cloudtrail_retention_days = 90
create_dns                = false
domain_name               = ""
hosted_zone_id            = ""
alarm_email               = ""
ses_identity_arn          = null
ses_sender_identity       = "devopslabinc.com"
request_ses_production_access = true
tags = {
  Owner      = "DevOpsLabCode"
  CostCenter = "DemandGig"
}

# Development backups remain deletable and avoid cold-storage minimums.
enable_backup_vault_lock          = false
backup_retention_days             = 35
backup_max_retention_days         = 120
backup_cold_storage_after_days    = null
backup_vault_lock_changeable_days = 3
enforce_production_readiness      = false
viewer_certificate_arn            = null
origin_certificate_arn            = null
