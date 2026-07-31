# Account security and Terraform control-plane foundation

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

This one-time Terraform root owns resources that are singletons at the AWS account or account/region level and provides the GitHub roles needed to operate the environment stacks safely.

## Controls owned here

- GitHub Actions IAM OIDC provider.
- Read-only Terraform plan role that can manage only native S3 `.tflock` files.
- Protected Terraform apply role using `PowerUserAccess` plus narrowly scoped IAM lifecycle permissions—not `AdministratorAccess`.
- Regional GuardDuty detector.
- Optional AWS Organizations auto-enrollment for all existing and future member accounts when this stack runs in the delegated GuardDuty administrator account.
- GuardDuty S3 data-event, EBS malware, and RDS login protections.
- Optional GuardDuty Runtime Monitoring with automatic ECS Fargate agent management.
- Optional Inspector-backed ECR enhanced continuous scanning.

Environment stacks create only application-release roles and read the shared OIDC provider and GuardDuty detector as data sources.

Set `enable_guardduty_organization_auto_enrollment = true` only in the delegated GuardDuty administrator account. Keep the default `false` in ordinary workload accounts; AWS rejects organization-configuration updates from non-administrator accounts.

## One-time bootstrap

The initial apply requires trusted local or administrative AWS credentials because GitHub OIDC and its roles do not exist yet.

```bash
./terraform/scripts/bootstrap-account.sh
terraform -chdir=terraform/global/account init -backend-config=backend.hcl
terraform -chdir=terraform/global/account plan
terraform -chdir=terraform/global/account apply
```

Then record the role outputs:

```bash
terraform -chdir=terraform/global/account output -raw terraform_plan_role_arn
terraform -chdir=terraform/global/account output -raw terraform_apply_role_arn
terraform -chdir=terraform/global/account output -raw terraform_permissions_boundary_arn
```

Configure these GitHub Actions secrets:

| Secret | Account-foundation output | Used by |
|---|---|---|
| `AWS_TERRAFORM_PLAN_ROLE_ARN` | `terraform_plan_role_arn` | Trusted post-merge development plans |
| `AWS_TERRAFORM_APPLY_ROLE_ARN` | `terraform_apply_role_arn` | Protected manual `dev`/`prod` deployments |

The workflow fails closed when either dedicated role secret is missing; it does not fall back to a broader legacy role.

## Trust boundary

- Pull requests run offline formatting, validation, TFLint, Checkov, and Go contract tests without AWS credentials or remote-state access.
- The AWS-backed development plan runs only after trusted code reaches `main` and uses the protected `dev` GitHub Environment.
- Apply-role trust excludes pull-request subjects by default and uses protected `dev`/`prod` environment subjects.
- Workflow-level permissions are read-only; only plan/deploy jobs receive `id-token: write`.
- IAM mutations are limited to the exact `demand-gig-engine-dev-*` and `demand-gig-engine-prod-*` role namespaces; the plan/apply roles are outside that scope.
- Every environment-created role must retain the partition-correct AWS-managed `PowerUserAccess` permissions boundary, preventing IAM-administration escalation.
- Managed policy attachment is restricted to the three service-role policies actually consumed by Backup, ECS task execution, and RDS Enhanced Monitoring.
- `iam:PassRole` is separated and constrained to exact environment role prefixes plus Backup, CloudTrail, ECS tasks, RDS enhanced monitoring, EventBridge Scheduler, and VPC Flow Logs service principals.
- The apply role deliberately lacks `iam:DeleteRolePermissionsBoundary`; removing a boundary requires a break-glass administrator.
- Service-linked role creation is constrained to the AWS services used by this framework.

## Lifecycle warnings

Do not destroy this stack during routine application teardown. Removing the OIDC provider breaks GitHub-to-AWS federation. Removing the GuardDuty detector disables detection and removes detector-owned findings.

Environment IAM roles are intentionally fail-closed: the Terraform apply role cannot remove their permissions boundary. A full environment destroy that reaches bounded IAM roles therefore requires an explicitly approved break-glass administrator to remove the boundary only after the workload has been decommissioned. This prevents a compromised deployment role from stripping the guardrail and escalating through a service role.
