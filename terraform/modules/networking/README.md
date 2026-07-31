# `networking` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Multi-tier network foundation

Creates the VPC, public/application/database subnets, internet and NAT paths, route tables, and S3 gateway endpoint.

## What this module does

- **Creates `aws_vpc.this`:** Creates the isolated virtual network that contains all environment resources.
- **Creates `aws_internet_gateway.this`:** Connects public subnets to the internet while private tiers remain route-controlled.
- **Creates `aws_subnet.public`:** Creates one subnet tier across the selected Availability Zones.
- **Creates `aws_subnet.app`:** Creates one subnet tier across the selected Availability Zones.
- **Creates `aws_subnet.db`:** Creates one subnet tier across the selected Availability Zones.
- **Creates `aws_eip.nat`:** Allocates stable public addresses used by NAT gateways.
- **Creates `aws_nat_gateway.this`:** Provides outbound internet access for private application subnets without accepting inbound connections.
- **Creates `aws_route_table.public`:** Defines how traffic leaves or moves within a subnet tier.
- **Creates `aws_route_table_association.public`:** Attaches a route table to the intended subnet.
- **Creates `aws_route_table.app`:** Defines how traffic leaves or moves within a subnet tier.
- **Creates `aws_route_table_association.app`:** Attaches a route table to the intended subnet.
- **Creates `aws_route_table.db`:** Defines how traffic leaves or moves within a subnet tier.
- **Creates `aws_route_table_association.db`:** Attaches a route table to the intended subnet.
- **Creates `aws_vpc_endpoint.s3`:** Keeps supported AWS service traffic on the AWS network instead of traversing the public internet.
- **Reads `aws_availability_zones.available`:** Read the currently available Availability Zones so subnet placement follows the target region.
- **Reads `aws_region.current`:** Read the active region to select the AWS-managed S3 prefix list for private endpoint routing.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `cidr` | `string` | `required` | `false` | IPv4 CIDR block allocated to the VPC. |
| `az_count` | `number` | `required` | `false` | Number of Availability Zones across which subnet tiers are created. |
| `nat_gateway_per_az` | `bool` | `false` | `false` | Whether each application Availability Zone receives its own NAT gateway for resilience. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `vpc_id` | ID of the VPC that owns the resource. | `aws_vpc.this.id` |
| `public_subnet_ids` | Public subnet IDs used by internet-facing load-balancing or NAT resources. | `[for s in aws_subnet.public :s.id]` |
| `app_subnet_ids` | Private application subnet IDs used by ECS workloads. | `[for s in aws_subnet.app :s.id]` |
| `db_subnet_ids` | Private database subnet IDs used by PostgreSQL or Redis. | `[for s in aws_subnet.db :s.id]` |

## Example

```hcl
module "networking" {
  source = "./modules/networking"
  name = var.name
  cidr = var.cidr
  az_count = var.az_count
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
