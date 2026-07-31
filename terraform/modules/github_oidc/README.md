# `github_oidc` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Keyless GitHub Actions deployment identity

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_openid_connect_provider.github`:** Registers GitHub's OIDC issuer for keyless federation.
- **`aws_iam_role.github`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.github`:** Grants resource-scoped permissions required by the role.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.tls_certificate.github`:** Reads the GitHub OIDC certificate chain used to register the identity provider.
- **Data `data.aws_iam_policy_document.assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `github_org` | `string` | `required` | `false` | Configuration value for `github_org`. |
| `github_repo` | `string` | `required` | `false` | Configuration value for `github_repo`. |
| `ecr_arns` | `list(string)` | `required` | `false` | Configuration value for `ecr_arns`. |
| `cluster_arn` | `string` | `required` | `false` | Configuration value for `cluster_arn`. |
| `allowed_branches` | `set(string)` | `["main"]` | `false` | Configuration value for `allowed_branches`. |
| `allowed_environments` | `set(string)` | `["dev", "prod"]` | `false` | Configuration value for `allowed_environments`. |
| `allow_pull_requests` | `bool` | `true` | `false` | Configuration value for `allow_pull_requests`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `role_arn` | Published `role_arn` value. | `aws_iam_role.github.arn` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

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
