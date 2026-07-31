locals {
  name = "${var.project_name}-${var.environment}"
  tags = merge(var.tags, { Environment = var.environment })
  origin_domain = var.domain_name == "" ? "" :"origin.${var.domain_name}"
  application_url = var.domain_name == "" ? "https://${module.cloudfront.domain_name}" :"https://${var.domain_name}"
  allowed_hosts = join(",", compact([var.domain_name, local.origin_domain, module.cloudfront.domain_name, module.alb.dns_name, "localhost", "127.0.0.1"]))
  provider_secret_keys = toset(["GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET","FACEBOOK_OAUTH_CLIENT_ID","FACEBOOK_OAUTH_CLIENT_SECRET","INSTAGRAM_OAUTH_CLIENT_ID","INSTAGRAM_OAUTH_CLIENT_SECRET","TIKTOK_OAUTH_CLIENT_KEY","TIKTOK_OAUTH_CLIENT_SECRET","STRIPE_SECRET_KEY","STRIPE_WEBHOOK_SECRET","META_APP_ID","META_APP_SECRET","META_PIXEL_ID","META_CONVERSIONS_API_TOKEN","VIBESMEET_ACCESS_TOKEN","VIBESMEET_WEBHOOK_SECRET",])
  provider_secrets = {for key in local.provider_secret_keys :key => "${module.secrets_manager.secret_arn}:${key}::"}
  common_environment = {
    DEBUG                   = "false",
    AWS_REGION              = var.aws_region,
    AWS_STORAGE_BUCKET_NAME = module.media.bucket_id,
    REDIS_URL               = "rediss://${module.redis.endpoint}:6379/0",
    SQS_QUEUE_URL           = module.sqs.queue_url,
    PUBLIC_BASE_URL         = local.application_url,
    FRONTEND_URL            = local.application_url,
    LOGIN_REDIRECT_URL      = local.application_url,
    ALLOWED_HOSTS           = local.allowed_hosts,
    CSRF_TRUSTED_ORIGINS    = local.application_url,
    CORS_ALLOWED_ORIGINS    = local.application_url,
    SECURE_SSL_REDIRECT     = "true",
    SECURE_PROXY_SSL_HEADER_NAME = "HTTP_X_FORWARDED_VIEWER_PROTO",
    SESSION_COOKIE_SECURE   = "true",
    CSRF_COOKIE_SECURE      = "true",
    PAYMENT_PROVIDER        = var.payment_provider,
    AWS_XRAY_DAEMON_ADDRESS = "127.0.0.1:2000",
    AWS_XRAY_ENABLED        = "true",
  }
  common_secrets = merge(local.provider_secrets, {
    DATABASE_URL = "${module.database.runtime_secret_arn}:DATABASE_URL::",
    SECRET_KEY   = "${module.database.runtime_secret_arn}:SECRET_KEY::",
  })
}
resource "random_password" "origin_verify" {
  length  = 48
  special = false
}

check "dns_configuration" {
  assert {
    condition = ! var.create_dns || (var.domain_name != "" && var.hosted_zone_id != "")
    error_message = "create_dns requires both domain_name and hosted_zone_id."
  }
}
check "production_safety" {
  assert {
    condition = var.allow_zero_capacity || var.environment != "prod" || (var.deletion_protection && var.db_multi_az && var.backend_desired_count >= 2 && var.redis_replicas >= 1)
    error_message = "Production requires deletion protection, Multi-AZ RDS, at least two API tasks, and a Redis replica."
  }
}
module "kms" {
  source = "./modules/kms"
  name = local.name
  tags = local.tags
}
module "networking" {
  source = "./modules/networking"
  name = local.name
  cidr = var.vpc_cidr
  az_count = var.az_count
  nat_gateway_per_az = var.nat_gateway_per_az
  tags = local.tags
}
module "security" {
  source          = "./modules/security"
  name            = local.name
  vpc_id          = module.networking.vpc_id
  alb_origin_port = var.create_dns ? 443 : 80
  tags            = local.tags
}
module "ecr" {
  source = "./modules/ecr"
  name = local.name
  repositories = ["backend","frontend"]
  kms_key_arn = module.kms.key_arn
  tags = local.tags
}
module "static" {
  source            = "./modules/s3_static"
  name              = "${local.name}-${data.aws_caller_identity.current.account_id}-static"
  force_destroy     = var.environment == "dev"
  create_tls_policy = false
  tags              = local.tags
}
module "media" {
  source            = "./modules/s3_static"
  name              = "${local.name}-${data.aws_caller_identity.current.account_id}-media"
  force_destroy     = var.environment == "dev"
  kms_key_arn       = module.kms.key_arn
  create_tls_policy = true
  tags              = local.tags
}
module "acm_viewer" {
  providers      = { aws = aws.us_east_1 }
  source         = "./modules/acm"
  domain_name    = var.domain_name
  hosted_zone_id = var.hosted_zone_id
  create         = var.create_dns
  tags           = local.tags
}

module "acm_origin" {
  source         = "./modules/acm"
  domain_name    = local.origin_domain
  hosted_zone_id = var.hosted_zone_id
  create         = var.create_dns
  tags           = local.tags
}
module "waf" {
  providers = {aws = aws.us_east_1}
  source = "./modules/waf"
  name = local.name
  tags = local.tags
}
module "alb" {
  source = "./modules/alb"
  name = local.name
  vpc_id = module.networking.vpc_id
  subnet_ids = module.networking.public_subnet_ids
  security_group_ids = [module.security.alb_sg_id]
  certificate_arn           = module.acm_origin.certificate_arn
  origin_verify_header_name = "X-Origin-Verify"
  origin_verify_header_value = random_password.origin_verify.result
  deletion_protection       = var.deletion_protection
  tags = local.tags
}
module "cloudfront" {
  source = "./modules/cloudfront"
  name = local.name
  bucket_id = module.static.bucket_id
  bucket_arn = module.static.bucket_arn
  bucket_domain_name = module.static.regional_domain_name
  alb_domain_name = var.create_dns ? local.origin_domain :module.alb.dns_name
  use_https_origin = var.create_dns
  domain_name = var.domain_name
  certificate_arn = module.acm_viewer.certificate_arn
  price_class = var.cloudfront_price_class
  web_acl_arn               = module.waf.arn
  origin_verify_header_name = "X-Origin-Verify"
  origin_verify_header_value = random_password.origin_verify.result
  tags                      = local.tags
}
module "route53" {
  source = "./modules/route53"
  enabled = var.create_dns
  zone_id = var.hosted_zone_id
  record_name = var.domain_name
  target_name = module.cloudfront.domain_name
  target_zone_id = module.cloudfront.hosted_zone_id
}
module "route53_origin" {
  source = "./modules/route53"
  enabled = var.create_dns
  zone_id = var.hosted_zone_id
  record_name = local.origin_domain
  target_name    = module.alb.dns_name
  target_zone_id = module.alb.zone_id
  create_ipv6    = false
}
module "database" {
  source = "./modules/rds_postgres"
  name = local.name
  subnet_ids = module.networking.db_subnet_ids
  security_group_ids = [module.security.db_sg_id]
  kms_key_arn = module.kms.key_arn
  instance_class = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  multi_az                    = var.db_multi_az
  performance_insights_enabled = var.db_performance_insights_enabled
  deletion_protection          = var.deletion_protection
  tags = local.tags
}
module "redis" {
  source = "./modules/redis"
  name = local.name
  subnet_ids = module.networking.db_subnet_ids
  security_group_ids = [module.security.redis_sg_id]
  kms_key_arn = module.kms.key_arn
  node_type = var.redis_node_type
  replicas = var.redis_replicas
  tags = local.tags
}
module "sqs" {
  source = "./modules/sqs"
  name = local.name
  tags = local.tags
}
module "eventbridge" {
  source = "./modules/eventbridge"
  name = local.name
  queue_arn = module.sqs.queue_arn
  dlq_arn = module.sqs.dlq_arn
  schedule_enabled = var.schedule_enabled
  tags = local.tags
}
module "secrets_manager" {
  source = "./modules/secrets_manager"
  name = local.name
  kms_key_arn = module.kms.key_arn
  tags = local.tags
}
module "ses" {
  source = "./modules/ses"
  domain_name = var.domain_name
  hosted_zone_id = var.hosted_zone_id
  create_dns = var.create_dns
}
module "cluster" {
  source = "./modules/ecs_cluster"
  name = local.name
  kms_key_arn = module.kms.key_arn
  tags = local.tags
}
module "backend" {
  source = "./modules/ecs_service"
  name = "${local.name}-api"
  cluster_arn = module.cluster.cluster_arn
  subnet_ids = module.networking.app_subnet_ids
  security_group_ids = [module.security.app_sg_id]
  image = var.backend_image
  cpu = var.backend_cpu
  memory = var.backend_memory
  desired_count = var.backend_desired_count
  target_group_arn      = module.alb.target_group_arn
  enable_execute_command = var.enable_execute_command
  kms_key_arn           = module.kms.key_arn
  queue_arn = module.sqs.queue_arn
  ses_identity_arn = module.ses.identity_arn
  object_storage_bucket_arn = module.media.bucket_arn
  environment = local.common_environment
  secrets = local.common_secrets
  tags = local.tags
}
module "worker" {
  source = "./modules/ecs_service"
  name = "${local.name}-worker"
  cluster_arn = module.cluster.cluster_arn
  subnet_ids = module.networking.app_subnet_ids
  security_group_ids = [module.security.app_sg_id]
  image = var.backend_image
  cpu = var.worker_cpu
  memory = var.worker_memory
  desired_count = var.worker_desired_count
  command = ["python","manage.py","process_tasks"]
  expose_port = false
  enable_health_check = false
  enable_autoscaling    = false
  enable_execute_command = var.enable_execute_command
  kms_key_arn           = module.kms.key_arn
  queue_arn = module.sqs.queue_arn
  ses_identity_arn = module.ses.identity_arn
  object_storage_bucket_arn = module.media.bucket_arn
  environment = local.common_environment
  secrets = local.common_secrets
  tags = local.tags
}
module "migration" {
  source                    = "./modules/ecs_service"
  name                      = "${local.name}-migration"
  cluster_arn               = module.cluster.cluster_arn
  subnet_ids                = module.networking.app_subnet_ids
  security_group_ids        = [module.security.app_sg_id]
  image                     = var.backend_image
  cpu                       = var.worker_cpu
  memory                    = var.worker_memory
  desired_count             = 0
  command                   = ["python", "manage.py", "migrate", "--noinput"]
  expose_port               = false
  enable_health_check       = false
  enable_autoscaling        = false
  enable_xray                = false
  enable_execute_command     = false
  kms_key_arn                = module.kms.key_arn
  queue_arn                 = module.sqs.queue_arn
  ses_identity_arn          = module.ses.identity_arn
  object_storage_bucket_arn = module.media.bucket_arn
  environment               = local.common_environment
  secrets                   = local.common_secrets
  tags                      = local.tags
}

module "github_oidc" {
  source                  = "./modules/github_oidc"
  name                    = "${local.name}-github"
  github_org              = var.github_org
  github_repo             = var.github_repo
  cluster_arn             = module.cluster.cluster_arn
  resource_name_prefix    = "${var.project_name}-"
  create_oidc_provider    = var.create_github_oidc_provider
  allowed_environments    = [var.environment]
  allowed_branches        = []
  allow_pull_requests     = false
  tags                    = local.tags
}
module "backup" {
  source = "./modules/backup"
  name = local.name
  kms_key_arn = module.kms.key_arn
  resource_arns = [module.database.db_arn]
  tags = local.tags
}
module "cloudwatch" {
  source = "./modules/cloudwatch"
  name = local.name
  alb_arn_suffix = split("loadbalancer/",module.alb.arn)[1]
  cluster_name = module.cluster.cluster_name
  service_name = module.backend.service_name
  sns_email = var.alarm_email
  tags = local.tags
}
module "cloudtrail" {
  source = "./modules/cloudtrail"
  name = local.name
  kms_key_arn = module.kms.key_arn
  retention_days = var.cloudtrail_retention_days
  tags = local.tags
}
module "guardduty" {
  source = "./modules/guardduty"
  enabled = var.enable_guardduty
  tags = local.tags
}
module "xray" {
  source = "./modules/xray"
  name = local.name
}
