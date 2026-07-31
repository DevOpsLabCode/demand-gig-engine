# `cloudwatch` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Encrypted operational alerting

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_sns_topic.alerts`:** Creates an encrypted notification or alarm topic.
- **`aws_sns_topic_policy.alerts`:** Restricts SNS administration, publication, and transport security.
- **`aws_sns_topic_subscription.email`:** Optionally delivers alarm notifications to an email endpoint.
- **`aws_cloudwatch_metric_alarm.alb_5xx`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.ecs_cpu`:** Raises an operational alarm when a service metric crosses its threshold.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_iam_policy_document.alerts`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `alb_arn_suffix` | `string` | `required` | `false` | Configuration value for `alb_arn_suffix`. |
| `cluster_name` | `string` | `required` | `false` | Configuration value for `cluster_name`. |
| `service_name` | `string` | `required` | `false` | Configuration value for `service_name`. |
| `sns_email` | `string` | `""` | `false` | Configuration value for `sns_email`. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key used to encrypt the alarm SNS topic. |
| `account_root_arn` | `string` | `required` | `false` | Owning account root ARN used by the explicit SNS administration policy. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| — | This module does not publish outputs. | — |

## Security and reliability controls

- KMS-encrypted alert topic.
- TLS-only SNS policy.
- ALB and ECS health alarms.

## Example

```hcl
module "cloudwatch" {
  source = "./modules/cloudwatch"
  name = var.name
  alb_arn_suffix = var.alb_arn_suffix
  cluster_name = var.cluster_name
  service_name = var.service_name
  kms_key_arn = var.kms_key_arn
  account_root_arn = var.account_root_arn
}
```

> The example shows the module contract only. Use `terraform/main.tf` for the complete dependency graph and production wiring.

## Validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
tflint --recursive
checkov -d .
python scripts/validate_security_remediation.py
```

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
