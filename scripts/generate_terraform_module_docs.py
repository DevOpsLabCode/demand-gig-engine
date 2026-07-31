#!/usr/bin/env python3
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Regenerates Terraform module READMEs from module source contracts.

"""Create accurate, source-derived README files for every Terraform module."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "terraform" / "modules"

PURPOSES = {
    "access_logs": "Centralized access-log storage",
    "acm": "TLS certificate provisioning",
    "alb": "Application ingress and origin TLS",
    "backup": "Immutable encrypted backups",
    "cloudfront": "Secure global content and API delivery",
    "cloudtrail": "Account activity audit trail",
    "cloudwatch": "Encrypted operational alerting",
    "ecr": "Encrypted container-image registries",
    "ecs_cluster": "ECS cluster and encrypted exec logging",
    "ecs_service": "Fargate workload, IAM, logging, and autoscaling",
    "eventbridge": "Encrypted campaign-expiry scheduling",
    "github_oidc": "Keyless GitHub Actions deployment identity",
    "guardduty": "Managed threat detection",
    "kms": "Customer-managed application encryption key",
    "networking": "Isolated multi-AZ VPC networking",
    "rds_postgres": "Resilient encrypted PostgreSQL and RDS Proxy",
    "redis": "Authenticated encrypted Redis",
    "route53": "DNS aliases for CloudFront and ALB",
    "s3_static": "Private versioned object storage",
    "secrets_manager": "Encrypted third-party integration secrets",
    "security": "Least-privilege network security groups",
    "ses": "Verified transactional-email identity",
    "sqs": "Encrypted work queue and dead-letter queue",
    "waf": "Managed web firewall and encrypted request logging",
    "xray": "Distributed tracing resources",
}

RESOURCE_DESCRIPTIONS = {
    "aws_lb": "Creates the Application Load Balancer and its security, deletion-protection, and access-log settings.",
    "aws_lb_listener": "Defines an HTTP redirect, restricted development origin, or HTTPS listener.",
    "aws_lb_target_group": "Registers ECS IP targets and defines application health checks.",
    "aws_cloudfront_distribution": "Delivers the React frontend and dynamic API routes through HTTPS and WAF.",
    "aws_cloudfront_origin_access_control": "Allows signed CloudFront access to the private S3 origin.",
    "aws_cloudfront_function": "Rewrites extensionless single-page application routes to the application shell.",
    "aws_cloudfront_response_headers_policy": "Adds browser security headers to CloudFront responses.",
    "aws_s3_bucket": "Creates private object storage for application data, state, or audit logs.",
    "aws_s3_bucket_policy": "Applies service-delivery permissions and denies insecure transport.",
    "aws_s3_bucket_logging": "Delivers source-bucket access records to the central log sink.",
    "aws_s3_bucket_lifecycle_configuration": "Aborts failed uploads and controls archival and expiration.",
    "aws_s3_bucket_server_side_encryption_configuration": "Encrypts new objects at rest.",
    "aws_s3_bucket_public_access_block": "Blocks public ACL and bucket-policy exposure.",
    "aws_s3_bucket_versioning": "Preserves historical object versions for recovery and investigation.",
    "aws_s3_bucket_ownership_controls": "Defines bucket ownership and log-delivery ACL behavior.",
    "aws_s3_bucket_acl": "Keeps the log destination private while supporting required delivery ACLs.",
    "aws_cloudtrail": "Records validated multi-region AWS API activity.",
    "aws_sns_topic": "Creates an encrypted notification or alarm topic.",
    "aws_sns_topic_policy": "Restricts SNS administration, publication, and transport security.",
    "aws_sns_topic_subscription": "Optionally delivers alarm notifications to an email endpoint.",
    "aws_cloudwatch_log_group": "Stores encrypted logs with a policy-enforced retention period.",
    "aws_cloudwatch_metric_alarm": "Raises an operational alarm when a service metric crosses its threshold.",
    "aws_ecs_cluster": "Creates the ECS control plane for Fargate services and tasks.",
    "aws_ecs_cluster_capacity_providers": "Configures Fargate capacity-provider behavior.",
    "aws_ecs_task_definition": "Defines containers, secrets, health checks, resource limits, and logging.",
    "aws_ecs_service": "Runs and maintains the requested number of private Fargate tasks.",
    "aws_appautoscaling_target": "Registers an ECS service as an autoscaling target.",
    "aws_appautoscaling_policy": "Scales the ECS service in response to utilization.",
    "aws_iam_role": "Creates a narrowly trusted service or deployment role.",
    "aws_iam_role_policy": "Grants resource-scoped permissions required by the role.",
    "aws_iam_role_policy_attachment": "Attaches an AWS managed service-role policy.",
    "aws_iam_openid_connect_provider": "Registers GitHub's OIDC issuer for keyless federation.",
    "aws_scheduler_schedule": "Runs the campaign-expiry task on an encrypted schedule with retries and a DLQ.",
    "aws_scheduler_schedule_group": "Groups related EventBridge Scheduler schedules.",
    "aws_cloudwatch_event_bus": "Creates the environment event bus.",
    "aws_kms_key": "Creates a rotating customer-managed encryption key with a constrained key policy.",
    "aws_kms_alias": "Publishes a stable human-readable alias for the KMS key.",
    "aws_vpc": "Creates the isolated network boundary.",
    "aws_subnet": "Creates public, application, or database subnets across Availability Zones.",
    "aws_internet_gateway": "Provides controlled internet routing for public subnets.",
    "aws_nat_gateway": "Provides outbound-only internet access for private application subnets.",
    "aws_route_table": "Defines subnet routing behavior.",
    "aws_route_table_association": "Associates a subnet with its intended route table.",
    "aws_flow_log": "Records accepted and rejected VPC traffic for security analysis.",
    "aws_default_security_group": "Removes rules from the VPC default security group.",
    "aws_security_group": "Creates a stateful least-privilege network boundary.",
    "aws_db_instance": "Creates encrypted Multi-AZ PostgreSQL with backups and deletion protection.",
    "aws_db_proxy": "Provides pooled TLS database connections using a protected secret.",
    "aws_db_proxy_default_target_group": "Defines RDS Proxy connection-pool behavior.",
    "aws_db_proxy_target": "Registers PostgreSQL as the RDS Proxy target.",
    "aws_db_subnet_group": "Places database resources in isolated subnets.",
    "aws_db_parameter_group": "Enforces database-engine settings such as PostgreSQL TLS.",
    "aws_secretsmanager_secret": "Creates a KMS-encrypted secret with a recovery window.",
    "aws_secretsmanager_secret_version": "Stores the generated runtime or integration value.",
    "aws_elasticache_replication_group": "Creates encrypted authenticated Redis with optional Multi-AZ failover.",
    "aws_elasticache_subnet_group": "Places Redis nodes in isolated database subnets.",
    "aws_sqs_queue": "Creates a KMS-encrypted task or dead-letter queue.",
    "aws_sqs_queue_policy": "Denies non-TLS queue access.",
    "aws_sqs_queue_redrive_allow_policy": "Limits which source queue may redrive messages from the DLQ.",
    "aws_backup_vault": "Stores recovery points under a customer-managed KMS key.",
    "aws_backup_vault_lock_configuration": "Makes backup retention immutable after the changeable grace period.",
    "aws_backup_plan": "Defines the backup schedule, cold-storage transition, and retention lifecycle.",
    "aws_backup_selection": "Selects the protected resources for the backup plan.",
    "aws_wafv2_web_acl": "Applies AWS managed rules and per-IP rate limiting at the edge.",
    "aws_wafv2_web_acl_logging_configuration": "Sends redacted full-request WAF logs to encrypted CloudWatch Logs.",
    "aws_ecr_repository": "Creates an encrypted image repository with immutable tags and scanning.",
    "aws_ecr_lifecycle_policy": "Expires unneeded container images according to retention policy.",
    "aws_guardduty_detector": "Enables managed AWS threat detection.",
    "aws_route53_record": "Creates an alias record for the selected AWS endpoint.",
    "aws_acm_certificate": "Requests a DNS-validated ACM certificate.",
    "aws_acm_certificate_validation": "Waits for successful ACM DNS validation.",
    "aws_ses_domain_identity": "Registers a domain identity for outbound mail.",
    "aws_ses_domain_dkim": "Creates DKIM tokens for authenticated email.",
    "random_password": "Generates a strong credential without storing plaintext in source control.",
}

DATA_DESCRIPTIONS = {
    "aws_caller_identity": "Reads the active AWS account for account-scoped ARNs and policies.",
    "aws_partition": "Keeps generated ARNs compatible with the active AWS partition.",
    "aws_region": "Reads the provider region for service principals and encryption contexts.",
    "aws_availability_zones": "Discovers available zones for deterministic multi-AZ placement.",
    "aws_ec2_managed_prefix_list": "Reads AWS-managed service network ranges for restricted ingress.",
    "aws_iam_policy_document": "Builds a structured IAM, resource, trust, or key policy.",
    "tls_certificate": "Reads the GitHub OIDC certificate chain used to register the identity provider.",
}

MODULE_SECURITY = {
    "access_logs": ["Private, versioned terminal log sink", "TLS-only bucket policy", "Abandoned multipart-upload cleanup", "365-day current-log retention by default"],
    "alb": ["Deletion protection enabled by default", "Central S3 access logging", "HTTPS with TLS 1.2/1.3 policy", "HTTP redirects to HTTPS when a certificate exists"],
    "backup": ["Customer-managed KMS encryption", "Vault Lock compliance controls", "365-day minimum retention", "KMS grants constrained to AWS resources"],
    "cloudfront": ["Viewer HTTPS redirection", "WAF association", "Standard access logging", "Private signed S3 origin"],
    "cloudtrail": ["Multi-region validated trail", "KMS encryption", "Encrypted SNS delivery notifications", "Versioned private S3 archive"],
    "cloudwatch": ["KMS-encrypted alert topic", "TLS-only SNS policy", "ALB and ECS health alarms"],
    "ecs_cluster": ["KMS-encrypted ECS Exec logs", "At least 365 days of log retention"],
    "ecs_service": ["Private Fargate networking", "KMS-encrypted logs retained at least 365 days", "Secrets injected by ARN", "Resource-scoped IAM except AWS APIs that cannot be scoped"],
    "eventbridge": ["Scheduler metadata encrypted by CMK", "Resource-scoped SQS and KMS permissions", "Retry and dead-letter handling"],
    "kms": ["Annual key rotation", "30-day deletion window by default", "Service principals constrained by account, source ARN, or encryption context"],
    "networking": ["No automatic public IP assignment", "Private application and database subnets", "Encrypted one-year VPC flow logs", "Empty default security group"],
    "rds_postgres": ["Multi-AZ and deletion protection enabled by default", "KMS encryption and enforced TLS", "30-day backups and 731-day Performance Insights", "RDS Proxy with protected credentials"],
    "redis": ["At-rest and in-transit encryption", "Generated authentication token", "Multi-AZ failover when replicas exist", "Authenticated TLS URL stored in Secrets Manager"],
    "security": ["CloudFront-only ALB ingress", "ALB-to-application port restriction", "Database and Redis ingress only from application tasks", "No all-protocol internet egress"],
    "sqs": ["Customer-managed KMS encryption", "TLS-only resource policies", "14-day DLQ retention", "Source-restricted redrive"],
    "waf": ["AWS managed rule groups", "Per-IP rate limiting", "KMS-encrypted 365-day logs", "Authorization and Cookie fields redacted"],
}

VARIABLE_DESCRIPTIONS = {
    "name": "Stable name prefix used for resource names and tags.",
    "vpc_id": "ID of the VPC that owns the resources.",
    "vpc_cidr": "Private VPC CIDR used to constrain east-west traffic.",
    "subnet_ids": "Subnet IDs that determine resource placement.",
    "security_group_ids": "Security groups attached to the resource.",
    "kms_key_arn": "Customer-managed KMS key ARN used for encryption.",
    "tags": "Common ownership, environment, cost, and governance tags.",
    "bucket_id": "S3 bucket name consumed by this module.",
    "bucket_arn": "S3 bucket ARN consumed by this module.",
    "bucket_domain_name": "Regional S3 endpoint used by CloudFront.",
    "certificate_arn": "ACM certificate ARN used for TLS; null enables the documented restricted development path.",
    "resource_arns": "ARNs of resources protected or accessed by this module.",
}


def find_blocks(text: str, kind: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(rf'\b{re.escape(kind)}\s+"([^"]+)"(?:\s+"([^"]+)")?\s*\{{')
    results = []
    for match in pattern.finditer(text):
        depth = 1
        index = match.end()
        state = "code"
        while index < len(text) and depth:
            char = text[index]
            nxt = text[index + 1] if index + 1 < len(text) else ""
            if state == "code":
                if char == '"':
                    state = "string"
                elif char == "#":
                    state = "line"
                elif char == "/" and nxt == "/":
                    state = "line"
                    index += 1
                elif char == "/" and nxt == "*":
                    state = "block"
                    index += 1
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
            elif state == "string":
                if char == "\\":
                    index += 1
                elif char == '"':
                    state = "code"
            elif state == "line":
                if char == "\n":
                    state = "code"
            elif state == "block":
                if char == "*" and nxt == "/":
                    state = "code"
                    index += 1
            index += 1
        results.append((match.group(1), match.group(2) or "", text[match.end(): index - 1]))
    return results


def attribute(body: str, name: str) -> str | None:
    match = re.search(rf'(?m)^\s*{re.escape(name)}\s*=\s*(.+?)\s*$', body)
    return match.group(1).strip() if match else None


def unquote(value: str | None) -> str | None:
    if value and len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def render_module(module: Path) -> str:
    name = module.name
    main = (module / "main.tf").read_text(encoding="utf-8")
    variables_text = (module / "variables.tf").read_text(encoding="utf-8") if (module / "variables.tf").exists() else ""
    outputs_text = (module / "outputs.tf").read_text(encoding="utf-8") if (module / "outputs.tf").exists() else ""

    resources = find_blocks(main, "resource")
    data_sources = find_blocks(main, "data")
    variables = find_blocks(variables_text, "variable")
    outputs = find_blocks(outputs_text, "output")

    lines = [
        f"# `{name}` Terraform module",
        "",
        "> **Author:** Stan Zvenigorodskiy  ",
        "> **Organization:** DevOps Lab Inc.  ",
        "> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)",
        "",
        f"## Purpose — {PURPOSES.get(name, name.replace('_', ' ').title())}",
        "",
        "This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.",
        "",
        "## Resources and data flow",
        "",
    ]
    if resources:
        for resource_type, resource_name, _ in resources:
            description = RESOURCE_DESCRIPTIONS.get(resource_type, f"Creates and manages `{resource_type}` for this module.")
            lines.append(f"- **`{resource_type}.{resource_name}`:** {description}")
    else:
        lines.append("- This module does not directly create Terraform resources.")
    for data_type, data_name, _ in data_sources:
        description = DATA_DESCRIPTIONS.get(data_type, f"Reads `{data_type}` metadata required by this module.")
        lines.append(f"- **Data `data.{data_type}.{data_name}`:** {description}")

    lines += ["", "## Inputs", "", "| Name | Type | Required/default | Sensitive | Description |", "|---|---|---|---|---|"]
    if variables:
        for var_name, _, body in variables:
            var_type = attribute(body, "type") or "any"
            default = attribute(body, "default")
            sensitive = attribute(body, "sensitive") or "false"
            description = unquote(attribute(body, "description")) or VARIABLE_DESCRIPTIONS.get(var_name, f"Configuration value for `{var_name}`.")
            requirement = "`required`" if default is None else f"`{default}`"
            lines.append(f"| `{var_name}` | `{var_type}` | {requirement} | `{sensitive}` | {description} |")
    else:
        lines.append("| — | — | — | — | This module has no input variables. |")

    lines += ["", "## Outputs", "", "| Name | Description | Value source |", "|---|---|---|"]
    if outputs:
        for output_name, _, body in outputs:
            description = unquote(attribute(body, "description")) or f"Published `{output_name}` value."
            value = attribute(body, "value") or "computed value"
            lines.append(f"| `{output_name}` | {description} | `{value}` |")
    else:
        lines.append("| — | This module does not publish outputs. | — |")

    controls = MODULE_SECURITY.get(name, [])
    lines += ["", "## Security and reliability controls", ""]
    if controls:
        lines.extend(f"- {control}." if not control.endswith(".") else f"- {control}" for control in controls)
    else:
        lines += [
            "- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.",
            "- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.",
        ]

    required_variables = [var_name for var_name, _, body in variables if attribute(body, "default") is None]
    lines += ["", "## Example", "", "```hcl", f'module "{name}" {{', f'  source = "./modules/{name}"']
    for var_name in required_variables:
        lines.append(f"  {var_name} = var.{var_name}")
    lines += ["}", "```", "", "> The example shows the module contract only. Use `terraform/main.tf` for the complete dependency graph and production wiring.", "", "## Validation", "", "```bash", "terraform fmt -check -recursive", "terraform init -backend=false", "terraform validate", "tflint --recursive", "checkov -d .", "python scripts/validate_security_remediation.py", "```", "", "See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).", ""]
    return "\n".join(lines)


def main() -> int:
    modules = sorted(path for path in MODULES.iterdir() if path.is_dir() and (path / "main.tf").exists())
    for module in modules:
        (module / "README.md").write_text(render_module(module), encoding="utf-8")
    print(f"Generated {len(modules)} Terraform module README files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
