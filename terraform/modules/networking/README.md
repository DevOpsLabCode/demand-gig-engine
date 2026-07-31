# `networking` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Isolated multi-AZ VPC networking

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_vpc.this`:** Creates the isolated network boundary.
- **`aws_default_security_group.this`:** Removes rules from the VPC default security group.
- **`aws_internet_gateway.this`:** Provides controlled internet routing for public subnets.
- **`aws_subnet.public`:** Creates public, application, or database subnets across Availability Zones.
- **`aws_subnet.app`:** Creates public, application, or database subnets across Availability Zones.
- **`aws_subnet.db`:** Creates public, application, or database subnets across Availability Zones.
- **`aws_eip.nat`:** Creates and manages `aws_eip` for this module.
- **`aws_nat_gateway.this`:** Provides outbound-only internet access for private application subnets.
- **`aws_route_table.public`:** Defines subnet routing behavior.
- **`aws_route_table_association.public`:** Associates a subnet with its intended route table.
- **`aws_route_table.app`:** Defines subnet routing behavior.
- **`aws_route_table_association.app`:** Associates a subnet with its intended route table.
- **`aws_route_table.db`:** Defines subnet routing behavior.
- **`aws_route_table_association.db`:** Associates a subnet with its intended route table.
- **`aws_vpc_endpoint.s3`:** Creates and manages `aws_vpc_endpoint` for this module.
- **`aws_cloudwatch_log_group.flow`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_iam_role.flow`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.flow`:** Grants resource-scoped permissions required by the role.
- **`aws_flow_log.this`:** Records accepted and rejected VPC traffic for security analysis.
- **Data `data.aws_availability_zones.available`:** Discovers available zones for deterministic multi-AZ placement.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_iam_policy_document.flow_assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `cidr` | `string` | `required` | `false` | Configuration value for `cidr`. |
| `az_count` | `number` | `required` | `false` | Configuration value for `az_count`. |
| `nat_gateway_per_az` | `bool` | `false` | `false` | Configuration value for `nat_gateway_per_az`. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key used by the VPC flow-log group. |
| `flow_log_retention_days` | `number` | `365` | `false` | Configuration value for `flow_log_retention_days`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `vpc_id` | Published `vpc_id` value. | `aws_vpc.this.id` |
| `public_subnet_ids` | Published `public_subnet_ids` value. | `[for s in aws_subnet.public :s.id]` |
| `app_subnet_ids` | Published `app_subnet_ids` value. | `[for s in aws_subnet.app :s.id]` |
| `db_subnet_ids` | Published `db_subnet_ids` value. | `[for s in aws_subnet.db :s.id]` |

## Security and reliability controls

- No automatic public IP assignment.
- Private application and database subnets.
- Encrypted one-year VPC flow logs.
- Empty default security group.

## Example

```hcl
module "networking" {
  source = "./modules/networking"
  name = var.name
  cidr = var.cidr
  az_count = var.az_count
  kms_key_arn = var.kms_key_arn
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
