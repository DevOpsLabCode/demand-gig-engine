# `github_oidc` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Keyless CI/CD access

Federates GitHub Actions to AWS through OIDC and grants a repository-scoped deployment role without permanent access keys.

## What this module does

- **Creates `aws_iam_openid_connect_provider.github`:** Registers GitHub Actions as a federated identity provider without static AWS keys.
- **Creates `aws_iam_role.github`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy.github`:** Attaches least-privilege inline permissions to the IAM role.
- **Reads `tls_certificate.github`:** Read GitHub token-service TLS certificates so the IAM OIDC provider uses the current root thumbprint.
- **Reads `aws_iam_policy_document.assume`:** Build the web-identity trust policy that limits role assumption to the approved GitHub repository subjects.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `github_org` | `string` | `required` | `false` | GitHub organization embedded in the trusted OIDC subject patterns. |
| `github_repo` | `string` | `required` | `false` | GitHub repository embedded in the trusted OIDC subject patterns. |
| `ecr_arns` | `list(string)` | `required` | `false` | ARNs of all ECR repositories controlled by the deployment role. |
| `cluster_arn` | `string` | `required` | `false` | ARN of the ECS cluster that will run this service. |
| `allowed_branches` | `set(string)` | `["main"]` | `false` | Branches encoded in the GitHub OIDC trust-policy subject conditions. |
| `allowed_environments` | `set(string)` | `["dev", "prod"]` | `false` | Protected GitHub environments encoded in the OIDC trust-policy subject conditions. |
| `allow_pull_requests` | `bool` | `true` | `false` | Whether pull-request subjects are included in the GitHub OIDC trust policy. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `role_arn` | ARN of the role resource consumed by this module. | `aws_iam_role.github.arn` |

## Example

```hcl
module "github_oidc" {
  source = "./modules/github_oidc"
  name = var.name
  github_org = var.github_org
  github_repo = var.github_repo
  ecr_arns = var.ecr_arns
  cluster_arn = var.cluster_arn
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
