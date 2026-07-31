# `ecs_service` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Reusable Fargate workload

Creates IAM roles, logs, task definitions, services, autoscaling, secrets, sidecars, and optional load-balancer integration for API or worker workloads.

## What this module does

- **Creates `aws_iam_role.execution`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy_attachment.execution`:** Attaches a managed IAM policy required by the role.
- **Creates `aws_iam_role_policy.secrets`:** Attaches least-privilege inline permissions to the IAM role.
- **Creates `aws_iam_role.task`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy.task`:** Attaches least-privilege inline permissions to the IAM role.
- **Creates `aws_cloudwatch_log_group.this`:** Stores application, task, or ECS Exec logs with controlled retention.
- **Creates `aws_ecs_task_definition.this`:** Defines immutable container, role, logging, health, and resource settings for a workload revision.
- **Creates `aws_ecs_service.this`:** Keeps the requested number of application tasks running and connected to networking and load balancing.
- **Creates `aws_appautoscaling_target.this`:** Registers the ECS service as a scalable target with capacity limits.
- **Creates `aws_appautoscaling_policy.cpu`:** Adjusts ECS task count in response to measured utilization.
- **Reads `aws_iam_policy_document.assume`:** Build the shared ECS task trust policy used by both execution and application task roles.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `cluster_arn` | `string` | `required` | `false` | ARN of the ECS cluster that will run this service. |
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine the private or public network placement of the resource. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the workload network interface. |
| `image` | `string` | `required` | `false` | Container image URI and tag or digest launched by the task definition. |
| `container_port` | `number` | `8000` | `false` | TCP port on which the application container listens. |
| `expose_port` | `bool` | `true` | `false` | Whether the ECS service should register the application port and load-balancer mapping. |
| `cpu` | `number` | `required` | `false` | Fargate CPU units reserved by the task definition. |
| `memory` | `number` | `required` | `false` | Memory in MiB reserved by the task definition. |
| `desired_count` | `number` | `required` | `false` | Number of service tasks Terraform requests at steady state. |
| `target_group_arn` | `string` | `null` | `false` | Optional ALB target-group ARN used to register this ECS service. |
| `command` | `list(string)` | `[]` | `false` | Optional container command that overrides the image default. |
| `environment` | `map(string)` | `{}` | `false` | Deployment environment name or the container environment-variable map, according to module context. |
| `secrets` | `map(string)` | `{}` | `false` | Map of container environment names to Secrets Manager or Parameter Store value ARNs. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets. |
| `queue_arn` | `string` | `required` | `false` | SQS queue ARN the task may read from or publish to. |
| `object_storage_bucket_arn` | `string` | `null` | `false` | Optional S3 bucket ARN the task may access for private application objects. |
| `enable_health_check` | `bool` | `true` | `false` | Whether the task definition includes the application container health check. |
| `enable_autoscaling` | `bool` | `true` | `false` | Whether Application Auto Scaling resources are created for the service. |
| `log_retention_days` | `number` | `30` | `false` | Number of days CloudWatch retains logs before automatic expiration. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |
| `ses_identity_arn` | `string` | `null` | `false` | Verified SES identity that tasks may use for outbound mail. |
| `enable_xray` | `bool` | `true` | `false` | Run the AWS X-Ray daemon sidecar and grant trace write permissions. |
| `xray_image` | `string` | `public.ecr.aws/xray/aws-xray-daemon:3.x` | `false` | Pinned AWS X-Ray daemon container image. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `service_name` | Name of the ECS service used by deployment, autoscaling, and monitoring commands. | `aws_ecs_service.this.name` |
| `service_arn` | ARN of the service resource consumed by this module. | `aws_ecs_service.this.id` |
| `task_role_arn` | ARN of the task role resource consumed by this module. | `aws_iam_role.task.arn` |
| `task_definition_arn` | ARN of the task definition resource consumed by this module. | `aws_ecs_task_definition.this.arn` |

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
