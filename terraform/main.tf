# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Composes reusable AWS modules into the complete Demand Gig Engine environment.
# Reading guide: Each comment explains why the following Terraform block exists.

# Compute reusable derived values used throughout this file.
locals {
  name = "${var.project_name}-${var.environment}"
  tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = "DevOps Lab Inc."
    Repository  = "${var.github_org}/${var.github_repo}"
  })
  permissions_boundary_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/PowerUserAccess"
  origin_domain            = var.domain_name == "" ? "" : "origin.${var.domain_name}"
  application_url          = var.domain_name == "" ? "https://${module.cloudfront.domain_name}" : "https://${var.domain_name}"
  allowed_hosts            = join(",", compact([var.domain_name, local.origin_domain, module.cloudfront.domain_name, module.alb.dns_name, "localhost", "127.0.0.1"]))
  provider_secret_keys     = toset(["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "FACEBOOK_OAUTH_CLIENT_ID", "FACEBOOK_OAUTH_CLIENT_SECRET", "INSTAGRAM_OAUTH_CLIENT_ID", "INSTAGRAM_OAUTH_CLIENT_SECRET", "TIKTOK_OAUTH_CLIENT_KEY", "TIKTOK_OAUTH_CLIENT_SECRET", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "META_APP_ID", "META_APP_SECRET", "META_PIXEL_ID", "META_CONVERSIONS_API_TOKEN", "VIBESMEET_ACCESS_TOKEN", "VIBESMEET_WEBHOOK_SECRET", ])
  provider_secrets         = { for key in local.provider_secret_keys : key => "${module.secrets_manager.secret_arn}:${key}::" }
  common_environment = {
    DEBUG                        = "false",
    AWS_REGION                   = var.aws_region,
    AWS_STORAGE_BUCKET_NAME      = module.media.bucket_id,
    SQS_QUEUE_URL                = module.sqs.queue_url,
    PUBLIC_BASE_URL              = local.application_url,
    FRONTEND_URL                 = local.application_url,
    LOGIN_REDIRECT_URL           = local.application_url,
    ALLOWED_HOSTS                = local.allowed_hosts,
    CSRF_TRUSTED_ORIGINS         = local.application_url,
    CORS_ALLOWED_ORIGINS         = local.application_url,
    SECURE_SSL_REDIRECT          = "false",
    SECURE_PROXY_SSL_HEADER_NAME = "HTTP_X_FORWARDED_VIEWER_PROTO",
    SESSION_COOKIE_SECURE        = "true",
    CSRF_COOKIE_SECURE           = "true",
    PAYMENT_PROVIDER             = var.payment_provider,
    AWS_XRAY_DAEMON_ADDRESS      = "127.0.0.1:2000",
    AWS_XRAY_ENABLED             = "true",
  }
  common_secrets = merge(local.provider_secrets, {
    DATABASE_URL = "${module.database.runtime_secret_arn}:DATABASE_URL::",
    SECRET_KEY   = "${module.database.runtime_secret_arn}:SECRET_KEY::",
    REDIS_URL    = "${module.redis.runtime_secret_arn}:REDIS_URL::",
  })
}
# Validates an invariant early so an unsafe or inconsistent plan cannot proceed.
check "dns_configuration" {
  assert {
    condition     = !var.create_dns || (var.domain_name != "" && var.hosted_zone_id != "")
    error_message = "create_dns requires both domain_name and hosted_zone_id."
  }
}
# Validates an invariant early so an unsafe or inconsistent plan cannot proceed.
check "production_safety" {
  assert {
    condition     = var.allow_zero_capacity || var.environment != "prod" || (var.deletion_protection && var.db_multi_az && var.backend_desired_count >= 2 && var.redis_replicas >= 1)
    error_message = "Production requires deletion protection, Multi-AZ RDS, at least two API tasks, and a Redis replica."
  }
}

# Prevent a production deployment from silently launching with demo integrations,
# no alert destination, or the default CloudFront hostname.
check "production_readiness" {
  assert {
    condition = (
      !var.enforce_production_readiness ||
      var.environment != "prod" ||
      (
        var.payment_provider != "fake" &&
        trimspace(var.alarm_email) != "" &&
        trimspace(var.domain_name) != "" &&
        (var.create_dns || (var.viewer_certificate_arn != null && var.origin_certificate_arn != null)) &&
        (var.create_dns || var.ses_identity_arn != null)
      )
    )
    error_message = "Production readiness requires a real payment provider, alarm_email, custom domain, and either Terraform-managed DNS validation or both existing viewer/origin ACM certificates."
  }
}
# Generate a high-entropy per-environment secret used only between CloudFront and
# the ALB. This closes the origin-bypass path that a prefix-list-only design leaves
# open to other AWS CloudFront distributions. The value is sensitive and remains
# encrypted in the Terraform backend.
resource "random_password" "origin_verify" {
  length  = 64
  special = false
}

# Invokes the reusable kms module and passes this environment configuration into it.
module "kms" {
  source = "./modules/kms"
  name   = local.name
  tags   = local.tags
}

# Central terminal log sink for ALB, CloudFront, source-bucket, and CloudTrail access records.
module "access_logs" {
  source        = "./modules/access_logs"
  name          = "${local.name}-${data.aws_caller_identity.current.account_id}-access-logs"
  force_destroy = var.environment == "dev"
  tags          = local.tags
}
# Invokes the reusable networking module and passes this environment configuration into it.
module "networking" {
  source                   = "./modules/networking"
  name                     = local.name
  cidr                     = var.vpc_cidr
  az_count                 = var.az_count
  nat_gateway_per_az       = var.nat_gateway_per_az
  kms_key_arn              = module.kms.key_arn
  permissions_boundary_arn = local.permissions_boundary_arn
  tags                     = local.tags
}
# Invokes the reusable security module and passes this environment configuration into it.
module "security" {
  source      = "./modules/security"
  name        = local.name
  vpc_id      = module.networking.vpc_id
  vpc_cidr    = var.vpc_cidr
  origin_port = module.acm_origin.certificate_arn != null ? 443 : 80
  tags        = local.tags
}
# Invokes the reusable ecr module and passes this environment configuration into it.
module "ecr" {
  source       = "./modules/ecr"
  name         = local.name
  repositories = ["backend", "frontend"]
  kms_key_arn  = module.kms.key_arn
  force_delete = var.environment == "dev"
  tags         = local.tags
}
# Invokes the reusable static module and passes this environment configuration into it.
module "static" {
  source               = "./modules/s3_static"
  name                 = "${local.name}-${data.aws_caller_identity.current.account_id}-static"
  force_destroy        = var.environment == "dev"
  create_tls_policy    = false
  access_log_bucket_id = module.access_logs.bucket_id
  tags                 = local.tags
}
# Invokes the reusable media module and passes this environment configuration into it.
module "media" {
  source               = "./modules/s3_static"
  name                 = "${local.name}-${data.aws_caller_identity.current.account_id}-media"
  force_destroy        = var.environment == "dev"
  kms_key_arn          = module.kms.key_arn
  create_tls_policy    = true
  access_log_bucket_id = module.access_logs.bucket_id
  tags                 = local.tags
}
# Invokes the reusable acm viewer module and passes this environment configuration into it.
module "acm_viewer" {
  providers                = { aws = aws.us_east_1 }
  source                   = "./modules/acm"
  domain_name              = var.domain_name
  hosted_zone_id           = var.hosted_zone_id
  create                   = var.create_dns
  existing_certificate_arn = var.viewer_certificate_arn
  tags                     = local.tags
}

# Invokes the reusable acm origin module and passes this environment configuration into it.
module "acm_origin" {
  source                   = "./modules/acm"
  domain_name              = local.origin_domain
  hosted_zone_id           = var.hosted_zone_id
  create                   = var.create_dns
  existing_certificate_arn = var.origin_certificate_arn
  tags                     = local.tags
}
# Invokes the reusable waf module and passes this environment configuration into it.
module "waf" {
  providers = { aws = aws.us_east_1 }
  source    = "./modules/waf"
  name      = local.name
  tags      = local.tags
}

# Protect the origin ALB independently from the CloudFront edge Web ACL.
module "waf_alb" {
  source = "./modules/waf"
  name   = "${local.name}-origin"
  scope  = "REGIONAL"
  tags   = local.tags
}
# Invokes the reusable alb module and passes this environment configuration into it.
module "alb" {
  source                     = "./modules/alb"
  name                       = local.name
  vpc_id                     = module.networking.vpc_id
  subnet_ids                 = module.networking.public_subnet_ids
  security_group_ids         = [module.security.alb_sg_id]
  certificate_arn            = module.acm_origin.certificate_arn
  deletion_protection        = var.deletion_protection
  access_log_bucket_id       = module.access_logs.bucket_id
  access_log_prefix          = "alb"
  origin_verify_header_value = random_password.origin_verify.result
  tags                       = local.tags
}

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = module.alb.arn
  web_acl_arn  = module.waf_alb.arn
}
# Invokes the reusable cloudfront module and passes this environment configuration into it.
module "cloudfront" {
  source                        = "./modules/cloudfront"
  name                          = local.name
  bucket_id                     = module.static.bucket_id
  bucket_arn                    = module.static.bucket_arn
  bucket_domain_name            = module.static.regional_domain_name
  alb_domain_name               = module.acm_origin.certificate_arn != null ? local.origin_domain : module.alb.dns_name
  use_https_origin              = module.acm_origin.certificate_arn != null
  origin_verify_header_value    = random_password.origin_verify.result
  domain_name                   = var.domain_name
  certificate_arn               = module.acm_viewer.certificate_arn
  price_class                   = var.cloudfront_price_class
  web_acl_arn                   = module.waf.arn
  access_log_bucket_domain_name = module.access_logs.bucket_domain_name
  tags                          = local.tags
}
# Invokes the reusable route53 module and passes this environment configuration into it.
module "route53" {
  source         = "./modules/route53"
  enabled        = var.create_dns
  zone_id        = var.hosted_zone_id
  record_name    = var.domain_name
  target_name    = module.cloudfront.domain_name
  target_zone_id = module.cloudfront.hosted_zone_id
}
# Invokes the reusable route53 origin module and passes this environment configuration into it.
module "route53_origin" {
  source         = "./modules/route53"
  enabled        = var.create_dns
  zone_id        = var.hosted_zone_id
  record_name    = local.origin_domain
  target_name    = module.alb.dns_name
  target_zone_id = module.alb.zone_id
  create_ipv6    = false
}
# Invokes the reusable database module and passes this environment configuration into it.
module "database" {
  source                      = "./modules/rds_postgres"
  name                        = local.name
  subnet_ids                  = module.networking.db_subnet_ids
  security_group_ids          = [module.security.db_sg_id]
  kms_key_arn                 = module.kms.key_arn
  instance_class              = var.db_instance_class
  allocated_storage           = var.db_allocated_storage
  multi_az                    = var.db_multi_az
  deletion_protection         = var.deletion_protection
  secret_recovery_window_days = var.environment == "prod" ? 30 : 7
  permissions_boundary_arn    = local.permissions_boundary_arn
  tags                        = local.tags
}
# Invokes the reusable redis module and passes this environment configuration into it.
module "redis" {
  source                  = "./modules/redis"
  name                    = local.name
  subnet_ids              = module.networking.db_subnet_ids
  security_group_ids      = [module.security.redis_sg_id]
  kms_key_arn             = module.kms.key_arn
  node_type               = var.redis_node_type
  replicas                = var.redis_replicas
  snapshot_retention_days = var.environment == "prod" ? 7 : 1
  apply_immediately       = false
  tags                    = local.tags
}
# Invokes the reusable sqs module and passes this environment configuration into it.
module "sqs" {
  source      = "./modules/sqs"
  name        = local.name
  kms_key_arn = module.kms.key_arn
  tags        = local.tags
}
# Invokes the reusable eventbridge module and passes this environment configuration into it.
module "eventbridge" {
  source                   = "./modules/eventbridge"
  name                     = local.name
  queue_arn                = module.sqs.queue_arn
  dlq_arn                  = module.sqs.dlq_arn
  kms_key_arn              = module.kms.key_arn
  schedule_enabled         = var.schedule_enabled
  permissions_boundary_arn = local.permissions_boundary_arn
  tags                     = local.tags
}
# Invokes the reusable secrets manager module and passes this environment configuration into it.
module "secrets_manager" {
  source                  = "./modules/secrets_manager"
  name                    = local.name
  kms_key_arn             = module.kms.key_arn
  recovery_window_in_days = var.environment == "prod" ? 30 : 7
  tags                    = local.tags
}
# Invokes the reusable ses module and passes this environment configuration into it.
module "ses" {
  source                = "./modules/ses"
  domain_name           = var.domain_name
  hosted_zone_id        = var.hosted_zone_id
  create_dns            = var.create_dns
  existing_identity_arn = var.ses_identity_arn
  dmarc_policy          = var.environment == "prod" ? "quarantine" : "none"
  dmarc_rua             = var.alarm_email
}
# Invokes the reusable cluster module and passes this environment configuration into it.
module "cluster" {
  source      = "./modules/ecs_cluster"
  name        = local.name
  kms_key_arn = module.kms.key_arn
  tags        = local.tags
}
# Invokes the reusable backend module and passes this environment configuration into it.
module "backend" {
  source                    = "./modules/ecs_service"
  name                      = "${local.name}-api"
  cluster_arn               = module.cluster.cluster_arn
  subnet_ids                = module.networking.app_subnet_ids
  security_group_ids        = [module.security.app_sg_id]
  image                     = var.backend_image
  ecr_repository_arns       = module.ecr.repository_arns
  cpu                       = var.backend_cpu
  memory                    = var.backend_memory
  desired_count             = var.backend_desired_count
  target_group_arn          = module.alb.target_group_arn
  kms_key_arn               = module.kms.key_arn
  queue_arn                 = module.sqs.queue_arn
  queue_actions             = ["sqs:GetQueueAttributes", "sqs:SendMessage"]
  ses_identity_arn          = module.ses.identity_arn
  object_storage_bucket_arn = module.media.bucket_arn
  environment               = local.common_environment
  secrets                   = local.common_secrets
  permissions_boundary_arn  = local.permissions_boundary_arn
  tags                      = local.tags
}
# Invokes the reusable worker module and passes this environment configuration into it.
module "worker" {
  source                    = "./modules/ecs_service"
  name                      = "${local.name}-worker"
  cluster_arn               = module.cluster.cluster_arn
  subnet_ids                = module.networking.app_subnet_ids
  security_group_ids        = [module.security.app_sg_id]
  image                     = var.backend_image
  ecr_repository_arns       = module.ecr.repository_arns
  cpu                       = var.worker_cpu
  memory                    = var.worker_memory
  desired_count             = var.worker_desired_count
  command                   = ["python", "manage.py", "process_tasks"]
  expose_port               = false
  enable_health_check       = false
  enable_autoscaling        = false
  kms_key_arn               = module.kms.key_arn
  queue_arn                 = module.sqs.queue_arn
  queue_actions             = ["sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ReceiveMessage"]
  ses_identity_arn          = module.ses.identity_arn
  object_storage_bucket_arn = module.media.bucket_arn
  environment               = local.common_environment
  secrets                   = local.common_secrets
  permissions_boundary_arn  = local.permissions_boundary_arn
  tags                      = local.tags
}
# Invokes the reusable migration module and passes this environment configuration into it.
module "migration" {
  source                    = "./modules/ecs_service"
  name                      = "${local.name}-migration"
  cluster_arn               = module.cluster.cluster_arn
  subnet_ids                = module.networking.app_subnet_ids
  security_group_ids        = [module.security.app_sg_id]
  image                     = var.backend_image
  ecr_repository_arns       = module.ecr.repository_arns
  cpu                       = var.worker_cpu
  memory                    = var.worker_memory
  desired_count             = 0
  command                   = ["python", "manage.py", "migrate", "--noinput"]
  expose_port               = false
  enable_health_check       = false
  enable_autoscaling        = false
  enable_xray               = false
  kms_key_arn               = module.kms.key_arn
  queue_arn                 = module.sqs.queue_arn
  queue_actions             = []
  ses_identity_arn          = null
  object_storage_bucket_arn = null
  environment               = local.common_environment
  secrets                   = local.common_secrets
  permissions_boundary_arn  = local.permissions_boundary_arn
  tags                      = local.tags
}

# Invokes the reusable github oidc module and passes this environment configuration into it.
module "github_oidc" {
  source                   = "./modules/github_oidc"
  name                     = "${local.name}-github"
  github_org               = var.github_org
  github_repo              = var.github_repo
  ecr_arns                 = module.ecr.repository_arns
  cluster_arn              = module.cluster.cluster_arn
  allow_pull_requests      = false
  permissions_boundary_arn = local.permissions_boundary_arn
  tags                     = local.tags
}
# Invokes the reusable backup module and passes this environment configuration into it.
module "backup" {
  source                         = "./modules/backup"
  name                           = local.name
  kms_key_arn                    = module.kms.key_arn
  resource_arns                  = [module.database.db_arn]
  enable_vault_lock              = var.enable_backup_vault_lock
  minimum_retention_days         = var.backup_retention_days
  maximum_retention_days         = var.backup_max_retention_days
  cold_storage_after_days        = var.backup_cold_storage_after_days
  vault_lock_changeable_for_days = var.backup_vault_lock_changeable_days
  permissions_boundary_arn       = local.permissions_boundary_arn
  tags                           = local.tags
}
# Invokes the reusable cloudwatch module and passes this environment configuration into it.
module "cloudwatch" {
  source                     = "./modules/cloudwatch"
  name                       = local.name
  alb_arn_suffix             = split("loadbalancer/", module.alb.arn)[1]
  target_group_arn_suffix    = module.alb.target_group_arn_suffix
  cluster_name               = module.cluster.cluster_name
  service_names              = [module.backend.service_name, module.worker.service_name]
  db_identifier              = module.database.db_identifier
  redis_replication_group_id = module.redis.replication_group_id
  queue_name                 = module.sqs.queue_name
  dlq_name                   = module.sqs.dlq_name
  cloudfront_distribution_id = module.cloudfront.distribution_id
  sns_email                  = var.alarm_email
  kms_key_arn                = module.kms.key_arn
  account_root_arn           = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
  tags                       = local.tags
}
# Invokes the reusable cloudtrail module and passes this environment configuration into it.
module "cloudtrail" {
  source                    = "./modules/cloudtrail"
  name                      = local.name
  kms_key_arn               = module.kms.key_arn
  retention_days            = var.cloudtrail_retention_days
  access_log_bucket_id      = module.access_logs.bucket_id
  s3_data_event_bucket_arns = var.environment == "prod" ? [module.static.bucket_arn, module.media.bucket_arn] : []
  enable_insights           = var.environment == "prod"
  permissions_boundary_arn  = local.permissions_boundary_arn
  tags                      = local.tags
}
# Invokes the reusable guardduty module and passes this environment configuration into it.
module "guardduty" {
  source  = "./modules/guardduty"
  enabled = var.enable_guardduty
}
# Invokes the reusable xray module and passes this environment configuration into it.
module "xray" {
  source = "./modules/xray"
  name   = local.name
}
