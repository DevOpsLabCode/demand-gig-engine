# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provisions encrypted PostgreSQL, subnet/parameter groups, enhanced monitoring, Secrets Manager credentials, and an optional RDS Proxy.
# Reading guide: Each comment explains why the following Terraform block exists.

# Build the trust policy that permits the RDS monitoring service to publish enhanced-monitoring metrics.
data "aws_iam_policy_document" "monitoring_assume" {
  # Allow the RDS monitoring service to assume the enhanced-monitoring IAM role.
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}
# Creates an IAM role with a narrowly defined trust relationship.
resource "aws_iam_role" "monitoring" {
  name = "${var.name}-rds-monitoring"
  assume_role_policy = data.aws_iam_policy_document.monitoring_assume.json
  tags = var.tags
}
# Attaches a managed IAM policy required by the role.
resource "aws_iam_role_policy_attachment" "monitoring" {
  role = aws_iam_role.monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
# Generates a high-entropy value without placing a human-selected password in source control.
resource "random_password" "db" {
  length = 32
  special = false
}
# Generates a high-entropy value without placing a human-selected password in source control.
resource "random_password" "django" {
  length = 64
  special = false
}
# Creates a protected secret container whose value is consumed at runtime.
resource "aws_secretsmanager_secret" "db" {
  name = "${var.name}/database"
  kms_key_id = var.kms_key_arn
  recovery_window_in_days = 7
  tags = var.tags
}
# Initializes or updates the JSON value stored in Secrets Manager.
resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({ username = "gigadmin", password = random_password.db.result })
}
# Restricts the database to private database subnets across Availability Zones.
resource "aws_db_subnet_group" "this" {
  name = var.name
  subnet_ids = var.subnet_ids
  tags = var.tags
}
# Creates the managed PostgreSQL database with encryption, backups, and production safety controls.
resource "aws_db_instance" "this" {
  identifier = var.name
  engine = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class
  allocated_storage = var.allocated_storage
  max_allocated_storage = var.allocated_storage * 5
  storage_type = "gp3"
  storage_encrypted = true
  kms_key_id = var.kms_key_arn
  db_name = "gigengine"
  username = "gigadmin"
  password = random_password.db.result
  multi_az = var.multi_az
  db_subnet_group_name = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids
  backup_retention_period = var.multi_az ? 30 :7
  backup_window = "03:00-04:00"
  maintenance_window = "sun:04:30-sun:05:30"
  deletion_protection = var.deletion_protection
  skip_final_snapshot = ! var.deletion_protection
  final_snapshot_identifier = var.deletion_protection ? "${var.name}-final" :null
  publicly_accessible = false
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot = true
  performance_insights_enabled = true
  performance_insights_kms_key_id = var.kms_key_arn
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.monitoring.arn
  enabled_cloudwatch_logs_exports = ["postgresql","upgrade"]
  apply_immediately = false
  tags = var.tags
  depends_on = [aws_iam_role_policy_attachment.monitoring]
}
# Build the trust policy that allows the managed RDS Proxy service to assume its Secrets Manager access role.
data "aws_iam_policy_document" "proxy_assume" {
  # Allow the managed RDS Proxy service to assume the role that reads database credentials.
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["rds.amazonaws.com"]
    }
  }
}
# Creates an IAM role with a narrowly defined trust relationship.
resource "aws_iam_role" "proxy" {
  name = "${var.name}-proxy"
  assume_role_policy = data.aws_iam_policy_document.proxy_assume.json
  tags = var.tags
}
# Attaches least-privilege inline permissions to the IAM role.
resource "aws_iam_role_policy" "proxy" {
  role = aws_iam_role.proxy.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.db.arn }, { Effect = "Allow", Action = ["kms:Decrypt"], Resource = var.kms_key_arn }] })
}
# Pools and manages database connections between ECS tasks and PostgreSQL.
resource "aws_db_proxy" "this" {
  name = var.name
  engine_family = "POSTGRESQL"
  role_arn = aws_iam_role.proxy.arn
  vpc_subnet_ids = var.subnet_ids
  vpc_security_group_ids = var.security_group_ids
  require_tls = true
  debug_logging = false
  auth {
    auth_scheme = "SECRETS"
    secret_arn = aws_secretsmanager_secret.db.arn
    iam_auth = "DISABLED"
  }
  tags = var.tags
  depends_on = [aws_iam_role_policy.proxy]
}
# Defines connection-pool behavior for the database proxy.
resource "aws_db_proxy_default_target_group" "this" {
  db_proxy_name = aws_db_proxy.this.name
  connection_pool_config {
    max_connections_percent = 90
    max_idle_connections_percent = 50
    connection_borrow_timeout = 120
  }
}
# Registers the PostgreSQL instance as a target behind the database proxy.
resource "aws_db_proxy_target" "this" {
  db_instance_identifier = aws_db_instance.this.identifier
  db_proxy_name = aws_db_proxy.this.name
  target_group_name = aws_db_proxy_default_target_group.this.name
}
# Creates a protected secret container whose value is consumed at runtime.
resource "aws_secretsmanager_secret" "runtime" {
  name = "${var.name}/runtime"
  kms_key_id = var.kms_key_arn
  recovery_window_in_days = 7
  tags = var.tags
}
# Initializes or updates the JSON value stored in Secrets Manager.
resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id = aws_secretsmanager_secret.runtime.id
  secret_string = jsonencode({ DATABASE_URL = "postgresql://gigadmin:${random_password.db.result}@${aws_db_proxy.this.endpoint}:5432/gigengine", SECRET_KEY = random_password.django.result })
}
