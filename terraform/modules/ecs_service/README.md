# `ecs_service` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Fargate workload, IAM, logging, and autoscaling

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_role.execution`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy_attachment.execution`:** Attaches an AWS managed service-role policy.
- **`aws_iam_role_policy.secrets`:** Grants resource-scoped permissions required by the role.
- **`aws_iam_role.task`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.task`:** Grants resource-scoped permissions required by the role.
- **`aws_cloudwatch_log_group.this`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_ecs_task_definition.this`:** Defines containers, secrets, health checks, resource limits, and logging.
- **`aws_ecs_service.this`:** Runs and maintains the requested number of private Fargate tasks.
- **`aws_appautoscaling_target.this`:** Registers an ECS service as an autoscaling target.
- **`aws_appautoscaling_policy.cpu`:** Scales the ECS service in response to utilization.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_iam_policy_document.assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `cluster_arn` | `string` | `required` | `false` | Configuration value for `cluster_arn`. |
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine resource placement. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the resource. |
| `image` | `string` | `required` | `false` | Configuration value for `image`. |
| `container_port` | `number` | `8000` | `false` | Configuration value for `container_port`. |
| `expose_port` | `bool` | `true` | `false` | Configuration value for `expose_port`. |
| `cpu` | `number` | `required` | `false` | Configuration value for `cpu`. |
| `memory` | `number` | `required` | `false` | Configuration value for `memory`. |
| `desired_count` | `number` | `required` | `false` | Configuration value for `desired_count`. |
| `target_group_arn` | `string` | `null` | `false` | Configuration value for `target_group_arn`. |
| `command` | `list(string)` | `[]` | `false` | Configuration value for `command`. |
| `environment` | `map(string)` | `{}` | `false` | Configuration value for `environment`. |
| `secrets` | `map(string)` | `{}` | `false` | Configuration value for `secrets`. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for encryption. |
| `queue_arn` | `string` | `required` | `false` | Configuration value for `queue_arn`. |
| `object_storage_bucket_arn` | `string` | `null` | `false` | Configuration value for `object_storage_bucket_arn`. |
| `enable_health_check` | `bool` | `true` | `false` | Configuration value for `enable_health_check`. |
| `enable_autoscaling` | `bool` | `true` | `false` | Configuration value for `enable_autoscaling`. |
| `log_retention_days` | `number` | `365` | `false` | CloudWatch application-log retention; one year is the security baseline. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |
| `ses_identity_arn` | `string` | `null` | `false` | Verified SES identity that tasks may use for outbound mail. |
| `enable_xray` | `bool` | `true` | `false` | Run the AWS X-Ray daemon sidecar and grant trace write permissions. |
| `xray_image` | `string` | `"public.ecr.aws/xray/aws-xray-daemon:3.x"` | `false` | Pinned AWS X-Ray daemon container image. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `service_name` | Published `service_name` value. | `aws_ecs_service.this.name` |
| `service_arn` | Published `service_arn` value. | `aws_ecs_service.this.id` |
| `task_role_arn` | Published `task_role_arn` value. | `aws_iam_role.task.arn` |
| `task_definition_arn` | Published `task_definition_arn` value. | `aws_ecs_task_definition.this.arn` |

## Security and reliability controls

- Private Fargate networking.
- KMS-encrypted logs retained at least 365 days.
- Secrets injected by ARN.
- Resource-scoped IAM except AWS APIs that cannot be scoped.

## Example

```hcl
module "ecs_service" {
  source = "./modules/ecs_service"
  name = var.name
  cluster_arn = var.cluster_arn
  subnet_ids = var.subnet_ids
  security_group_ids = var.security_group_ids
  image = var.image
  cpu = var.cpu
  memory = var.memory
  desired_count = var.desired_count
  kms_key_arn = var.kms_key_arn
  queue_arn = var.queue_arn
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
