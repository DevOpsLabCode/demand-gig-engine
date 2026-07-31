# `ecs_service` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Fargate workload, IAM, logging, and autoscaling

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_role.execution`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.execution`:** Grants resource-scoped permissions required by the role.
- **`aws_iam_role.task`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.task`:** Grants resource-scoped permissions required by the role.
- **`aws_cloudwatch_log_group.this`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_ecs_task_definition.this`:** Defines containers, secrets, health checks, resource limits, and logging.
- **`aws_ecs_service.this`:** Runs and maintains the requested number of private Fargate tasks.
- **`aws_appautoscaling_target.this`:** Registers an ECS service as an autoscaling target.
- **`aws_appautoscaling_policy.cpu`:** Scales the ECS service in response to utilization.
- **`aws_appautoscaling_policy.memory`:** Scales the ECS service in response to utilization.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_iam_policy_document.assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable ECS service, task family, role, and log-group name prefix. |
| `cluster_arn` | `string` | `required` | `false` | ARN of the ECS cluster that runs the service. |
| `subnet_ids` | `list(string)` | `required` | `false` | Private application subnet IDs used by Fargate ENIs. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to Fargate ENIs. |
| `ecr_repository_arns` | `list(string)` | `required` | `false` | Exact ECR repository ARNs from which the task execution role may pull application images. |
| `image` | `string` | `required` | `false` | Container image URI with an explicit tag or digest. |
| `container_port` | `number` | `8000` | `false` | TCP port on which the application container listens. |
| `expose_port` | `bool` | `true` | `false` | Register an application port and optional load-balancer mapping. |
| `cpu` | `number` | `required` | `false` | Fargate task CPU units. |
| `memory` | `number` | `required` | `false` | Fargate task memory in MiB. |
| `desired_count` | `number` | `required` | `false` | Steady-state service task count. |
| `target_group_arn` | `string` | `null` | `false` | Optional ALB target-group ARN used by an exposed service. |
| `command` | `list(string)` | `[]` | `false` | Optional container command override. |
| `environment` | `map(string)` | `{}` | `false` | Non-sensitive container environment variables. |
| `secrets` | `map(string)` | `{}` | `false` | Container environment names mapped to Secrets Manager value references. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used by logs, secrets, queues, and object storage. |
| `queue_arn` | `string` | `required` | `false` | SQS queue ARN the application can consume and publish. |
| `queue_actions` | `set(string)` | `[` | `false` | Exact SQS data-plane actions granted to this workload; use an empty set for migrations. |
| `object_storage_bucket_arn` | `string` | `null` | `false` | Optional private S3 bucket ARN used for application objects. |
| `enable_health_check` | `bool` | `true` | `false` | Add the application-container health check. |
| `enable_autoscaling` | `bool` | `true` | `false` | Create Application Auto Scaling target and CPU policy. |
| `autoscaling_max_capacity` | `number` | `null` | `false` | Optional explicit autoscaling maximum; null uses four times desired count with a floor of two. |
| `autoscaling_cpu_target` | `number` | `60` | `false` | Average ECS CPU percentage targeted by autoscaling. |
| `autoscaling_memory_target` | `number` | `70` | `false` | Average ECS memory percentage targeted by the optional memory autoscaling policy. |
| `log_retention_days` | `number` | `365` | `false` | CloudWatch application-log retention; one year is the security baseline. |
| `ses_identity_arn` | `string` | `null` | `false` | Optional verified SES identity that tasks may use for outbound mail. |
| `enable_xray` | `bool` | `true` | `false` | Run the AWS X-Ray daemon sidecar and grant trace write permissions. |
| `xray_image` | `string` | `"public.ecr.aws/xray/aws-xray-daemon:3.6.6"` | `false` | Pinned AWS X-Ray daemon container image. The daemon is in maintenance mode; migrate to ADOT/OpenTelemetry before end of support. |
| `permissions_boundary_arn` | `string` | `required` | `false` | AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

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
  ecr_repository_arns = var.ecr_repository_arns
  image = var.image
  cpu = var.cpu
  memory = var.memory
  desired_count = var.desired_count
  kms_key_arn = var.kms_key_arn
  queue_arn = var.queue_arn
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
