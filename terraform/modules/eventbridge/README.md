# `eventbridge` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Encrypted campaign-expiry scheduling

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_role.scheduler`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.scheduler`:** Grants resource-scoped permissions required by the role.
- **`aws_scheduler_schedule_group.this`:** Groups related EventBridge Scheduler schedules.
- **`aws_scheduler_schedule.campaign_expiry`:** Runs the campaign-expiry task on an encrypted schedule with retries and a DLQ.
- **Data `data.aws_iam_policy_document.scheduler_assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable Scheduler group, role, and schedule name prefix. |
| `queue_arn` | `string` | `required` | `false` | SQS source queue ARN that receives campaign-expiry scan requests. |
| `dlq_arn` | `string` | `required` | `false` | SQS dead-letter queue ARN used when Scheduler delivery is exhausted. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used by Scheduler and the encrypted queues. |
| `schedule_enabled` | `bool` | `true` | `false` | Enable or disable the campaign-expiry schedule without deleting it. |
| `schedule_expression` | `string` | `"rate(5 minutes)"` | `false` | AWS Scheduler cron(...) or rate(...) expression. |
| `maximum_event_age_seconds` | `number` | `3600` | `false` | Maximum age of an undelivered scheduled event before it is discarded. |
| `maximum_retry_attempts` | `number` | `3` | `false` | Scheduler delivery retry attempts before the event is sent to the DLQ. |
| `permissions_boundary_arn` | `string` | `required` | `false` | AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `schedule_arn` | Campaign-expiry Scheduler ARN. | `aws_scheduler_schedule.campaign_expiry.arn` |
| `schedule_group_name` | Scheduler group name. | `aws_scheduler_schedule_group.this.name` |

## Security and reliability controls

- Scheduler metadata encrypted by CMK.
- Resource-scoped SQS and KMS permissions.
- Retry and dead-letter handling.

## Example

```hcl
module "eventbridge" {
  source = "./modules/eventbridge"
  name = var.name
  queue_arn = var.queue_arn
  dlq_arn = var.dlq_arn
  kms_key_arn = var.kms_key_arn
  permissions_boundary_arn = var.permissions_boundary_arn
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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
