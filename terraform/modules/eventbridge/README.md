# `eventbridge` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Scheduled campaign processing

Creates the event bus, scheduler role, schedule group, and recurring message that asks the SQS worker to expire due campaigns.

## What this module does

- **Creates `aws_iam_role.scheduler`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy.scheduler`:** Attaches least-privilege inline permissions to the IAM role.
- **Creates `aws_cloudwatch_event_bus.this`:** Creates a logical event channel for future event-driven integrations.
- **Creates `aws_scheduler_schedule_group.this`:** Groups related EventBridge Scheduler definitions for organization and lifecycle management.
- **Creates `aws_scheduler_schedule.campaign_expiry`:** Invokes the configured target on a managed schedule without running a dedicated cron server.
- **Reads `aws_iam_policy_document.scheduler_assume`:** Build the trust policy that permits only EventBridge Scheduler to assume the queue-delivery role.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `queue_arn` | `string` | `required` | `false` | SQS queue ARN the task may read from or publish to. |
| `dlq_arn` | `string` | `required` | `false` | Dead-letter queue ARN that receives messages after retries are exhausted. |
| `schedule_enabled` | `bool` | `true` | `false` | Whether the campaign-expiry schedule is active. |
| `schedule_expression` | `string` | `rate(5 minutes)` | `false` | EventBridge Scheduler expression controlling when the campaign-expiry job runs. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `event_bus_arn` | ARN of the event bus resource consumed by this module. | `aws_cloudwatch_event_bus.this.arn` |
| `schedule_arn` | ARN of the schedule resource consumed by this module. | `aws_scheduler_schedule.campaign_expiry.arn` |

## Example

```hcl
module "eventbridge" {
  source = "./modules/eventbridge"
  name = var.name
  queue_arn = var.queue_arn
  dlq_arn = var.dlq_arn
}
```

> The root `terraform/main.tf` contains the authoritative production composition. The example above shows the module interface, not a complete standalone deployment.

## Security and reliability notes

- Review every input before production use; defaults are conveniences, not substitutes for environment-specific risk review.
- Keep secret values in AWS Secrets Manager or protected CI/CD secrets. Do not place credentials in `.tfvars` committed to Git.
- Run `terraform fmt`, `terraform validate`, TFLint, Checkov, and the Go contract tests before applying changes.
- Inspect the plan for replacement, deletion, public exposure, IAM expansion, encryption changes, and cross-account effects.

## Files

- `main.tf` - resources and service configuration.
- `variables.tf` - input contract, validation, and defaults.
- `outputs.tf` - values exposed to callers when present.

## Validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
tflint --recursive
checkov -d .
```

See [`../../README.md`](../../README.md) for environment deployment and [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md) for the complete architecture.
