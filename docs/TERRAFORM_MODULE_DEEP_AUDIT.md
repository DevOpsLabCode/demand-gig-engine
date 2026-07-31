# Terraform module deep audit

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)  
> **Scope:** 25 reusable modules, 31 root module instances, two independent global roots, CI validation, environment wiring, and operational prerequisites.

## Executive result

The framework has a secure single-region AWS production baseline for the Demand Gig Engine, subject to the explicitly listed external production inputs and provider lock-file generation. Every local module is declared, wired, documented, and covered by static contract tests. The audit corrected environment-breaking defaults, added missing observability and email-authentication controls, isolated account-wide singleton resources, strengthened variable validation, and added fail-closed production readiness checks.

Automated guards now verify:

- all 25 module directories exist;
- every `var.*` reference is declared;
- every required module input is supplied;
- no root module passes unknown arguments;
- every `module.<instance>.<output>` reference exists;
- all three independent Terraform roots are validated in GitHub Actions;
- production cannot deploy with fake payments, no alert recipient, or no custom TLS domain;
- shared GitHub OIDC and GuardDuty resources cannot collide across `dev` and `prod` state;
- every environment-created IAM role uses the approved permissions boundary;
- the Terraform apply role can manage only exact `dev`/`prod` workload-role namespaces, cannot rewrite its own control-plane roles, and cannot remove role boundaries;
- managed policy attachments and `iam:PassRole` are allowlisted;
- CloudFront never forwards the viewer `Host` header to the TLS origin and keeps authenticated viewer-IP metadata out of the share-page cache key;
- RDS PostgreSQL/upgrade and Redis engine/slow logs are encrypted and retained for at least one year;
- API, worker, and migration task roles receive different queue/data permissions;
- bootstrap state is created only through the KMS-backed Terraform bootstrap root;
- deployments run migrations before rolling service updates without scaling live services to zero.

## Module-by-module findings

| Module | Deep-audit result | Controls confirmed or added | Operational boundary |
|---|---|---|---|
| `access_logs` | Ready | Dedicated private/versioned terminal S3 log sink; public-access block; AES-256; lifecycle transition and expiration; ALB, CloudFront canonical-user, and S3 delivery policies; TLS-only requests; validated bucket names and retention. | A terminal log sink intentionally cannot server-log to itself. Cross-region immutable archival belongs in a separate DR/security account. |
| `acm` | Ready | DNS-validated certificate creation, create-before-destroy, SAN support, and reuse of externally managed ACM ARNs. Root creates separate viewer and origin certificates in the correct regions. | Domain ownership and Route 53 zone access are required external trust inputs. |
| `alb` | Ready | CloudFront-only ingress, invalid-header dropping, strict desync mitigation, access logs, deletion protection, health checks, TLS 1.2/1.3, HTTP redirect, regional WAF association, and default-deny listener rules requiring a generated origin-verification secret. | The no-domain development path uses restricted HTTP from CloudFront because AWS-generated ALB names cannot receive ACM certificates. Production readiness forbids this path. |
| `backup` | Ready | KMS-encrypted vault, daily plan, configurable warm/cold retention, production Compliance Vault Lock, conditional development lock, bounded service role, grant constraints, and RDS selection. | Restore drills and cross-account copy destinations are operational/DR procedures and require a destination account. |
| `cloudfront` | Ready | Private S3 OAC, SPA rewrite, WAF, standard logs, HTTP/2 and HTTP/3, TLS, security headers, dedicated API/share cache and origin-request policies, API no-cache behavior, short share caching, authenticated viewer-IP propagation excluded from the cache key, a generated ALB origin header, and explicit origin forwarding that never forwards viewer `Host` to the origin certificate. | Multi-region origin failover is intentionally outside this single-region stack. Geo blocking is intentionally disabled for a global events platform. |
| `cloudtrail` | Ready | Multi-region management events, log validation, CMK encryption, versioned S3 archive, centralized S3 access logs, bounded CloudWatch delivery role, encrypted SNS notifications, production S3 object data events, and production API call/error Insights. | AWS Organizations organization-trail ownership should be moved to a delegated security account when a multi-account organization is established. |
| `cloudwatch` | Ready | Encrypted TLS-only SNS, ALB/target errors, unhealthy targets, p95 latency, API and worker CPU/memory, SQS backlog/age/DLQ, RDS CPU/storage, Redis CPU/memory/evictions, CloudFront 5xx, and a service dashboard. | Email subscriptions require recipient confirmation. Pager/on-call integrations require externally supplied endpoints. |
| `ecr` | Ready | Immutable tags, CMK encryption, scan on push, rollback image retention, and exact repository outputs. The account foundation adds Inspector-backed continuous enhanced scanning. | Image promotion/signing policy can be added when a separate release account or signing authority exists. |
| `ecs_cluster` | Ready | Enhanced Container Insights and CMK-encrypted one-year ECS Exec audit logging. | ECS Exec access must remain controlled by IAM and operational approval outside this module. |
| `ecs_service` | Ready | Separate permissions-bounded execution/task roles, exact ECR/log/secret permissions, workload-specific SQS actions, non-root containers, read-only root filesystem, dropped capabilities, writable `/tmp`, health checks, deployment rollback, private networking, CPU and memory autoscaling, ECS-managed tags, encrypted logs, optional S3/SES access, and migration-task reuse. | The X-Ray daemon is retained for compatibility but should migrate to AWS Distro for OpenTelemetry before long-term X-Ray SDK/daemon retirement. |
| `eventbridge` | Ready | Customer-managed encryption, Scheduler group, permissions-bounded exact SQS target role, DLQ, retry policy, event age, and enable/disable control. | Business cadence remains environment-configurable. |
| `github_oidc` | Ready | Reads the shared account OIDC provider, creates permissions-bounded environment-specific release roles, exact repository/protected-environment subjects by default, optional explicit branch subjects, PR trust disabled, ECR repository scope, and ECS cluster service scope. | `terraform/global/account` must be applied once before environment planning. Protected GitHub environments remain a GitHub-side prerequisite. |
| `guardduty` | Ready | Verifies the shared regional detector exists instead of creating duplicate detectors in every environment state. | Detector lifecycle and advanced features are owned by `terraform/global/account`; organization-wide delegation belongs in the security account. |
| `kms` | Ready | Rotation, 30-day deletion window, explicit key policy, CloudWatch Logs contexts, CloudTrail contexts, encrypted SNS publishers, and EventBridge Scheduler use. | The owning account root remains the break-glass key administrator; enterprise deployments should replace this with named security administration roles. |
| `networking` | Ready | Three subnet tiers across two/three AZs, no automatic public IPs, NAT per AZ in production, isolated DB routes, default SG deny, S3 gateway endpoint, encrypted one-year flow logs with a bounded delivery role, and CIDR/AZ validation. | Interface endpoints for ECR, Logs, Secrets Manager, and SSM can reduce NAT traffic but add hourly cost; NAT is retained as the universal provider/API path. |
| `rds_postgres` | Ready | Private encrypted PostgreSQL, Multi-AZ production, autoscaling gp3 storage, deletion protection, unique final snapshots, automated backups, CMK Performance Insights, bounded enhanced-monitoring/proxy roles, forced TLS, RDS Proxy, encrypted secrets, environment-aware recovery windows, and pre-created CMK-encrypted one-year PostgreSQL/upgrade log groups. | Generated database credentials remain in encrypted Terraform state because the application currently consumes a password URL. A future IAM-auth-only application path can remove this dependency. |
| `redis` | Ready | CMK encryption, TLS, generated auth token, encrypted runtime URL, private subnets, snapshots, maintenance windows, production replicas/failover, valid single-node development mode, and CMK-encrypted one-year engine/slow-query log delivery. | Global datastore/cross-region failover is a DR-layer decision. |
| `route53` | Ready | Optional A/AAAA aliases with prerequisite checks; root correctly disables AAAA for the IPv4 ALB origin and enables it for CloudFront. | Existing records must be imported or managed outside Terraform before enabling DNS. |
| `s3_static` | Ready | Private access, ownership enforcement, public-access block, versioning, encryption, server-access logs, abandoned upload cleanup, noncurrent expiration, and TLS-only policy ownership. | CloudFront owns the complete static-bucket access policy when OAC is enabled, avoiding competing S3 bucket policies. |
| `secrets_manager` | Ready | CMK-encrypted provider credential container, stable schema, environment-aware deletion recovery, and lifecycle protection against Terraform overwriting rotated values. | OAuth, Stripe, Meta, TikTok, Google, and VibesMeet secrets must be rotated with their issuing providers; no generic Lambda can safely rotate all of them. |
| `security` | Ready | CloudFront managed-prefix ingress to ALB, SG-to-SG API ingress, DB/Redis isolation, exact application ports, DNS, HTTPS egress, and constrained ALB egress. | Third-party APIs require internet HTTPS egress through NAT. More restrictive egress requires a maintained proxy/domain allowlist. |
| `ses` | Ready | Domain verification, Easy DKIM, custom MAIL FROM, MX, SPF, strict alignment, DMARC, and reject-on-MX-failure behavior. Production defaults to `quarantine`; development defaults to `none`. | SES production access, sending limits, reputation monitoring, and mailbox ownership are AWS/account operations. DMARC can be moved to `reject` after report review. |
| `sqs` | Ready | Source queue and DLQ CMK encryption, long polling, retention controls, visibility timeout, TLS-only policies, controlled redrive, and Scheduler-compatible outputs. | Queue thresholds should be tuned from production throughput after launch. |
| `waf` | Ready | CloudFront and regional ALB ACL instances, AWS managed common/IP-reputation/bad-input/SQLi rules, edge and authenticated-viewer-IP regional rate limiting, metrics, CMK-encrypted one-year full logs, and authorization/cookie/origin-secret redaction. | Managed rule exclusions and rate thresholds require tuning against real traffic to avoid false positives. |
| `xray` | Ready with migration plan | Configurable sampling priority, reservoir, fixed rate, and match scope; rule identifiers are output for governance. | X-Ray SDK/daemon support is in maintenance mode; use ADOT/OpenTelemetry for new instrumentation and plan migration of the existing sidecar. |

## Account-level foundation

`terraform/global/account` is a separate one-time Terraform root because these resources are account or account/region singletons:

- GitHub Actions IAM OIDC provider;
- separate read-only post-merge plan and protected apply roles;
- GuardDuty detector;
- GuardDuty S3, EBS malware, RDS login, and Runtime Monitoring features;
- automatic GuardDuty ECS Fargate agent management;
- ECR enhanced continuous scanning.

Pull requests never receive AWS credentials or remote-state access. The supplied workflow performs an AWS-backed development plan only after trusted code reaches `main`. The apply role is excluded from its own mutable resource scope, workload roles are restricted to exact `dev`/`prod` namespaces, every workload role must retain `PowerUserAccess` as a permissions boundary, managed policy attachments are allowlisted, and `iam:PassRole` is limited to exact role namespaces and service principals. The apply role intentionally cannot call `iam:DeleteRolePermissionsBoundary`; full IAM-role teardown requires approved break-glass administration.

Bootstrap it with trusted local AWS credentials before relying on GitHub OIDC. The stack outputs separate plan and apply role ARNs, eliminating the previous control-plane permission gap:

```bash
./terraform/scripts/bootstrap-account.sh
terraform -chdir=terraform/global/account init -backend-config=backend.hcl
terraform -chdir=terraform/global/account plan
terraform -chdir=terraform/global/account apply
terraform -chdir=terraform/global/account output -raw terraform_plan_role_arn
terraform -chdir=terraform/global/account output -raw terraform_apply_role_arn
terraform -chdir=terraform/global/account output -raw terraform_permissions_boundary_arn
```

## State bootstrap and deployment safety

`terraform/global/bootstrap` is the only supported owner of the `account`, `dev`, and `prod` state buckets, KMS aliases, versioning, logging, lifecycle, public-access blocks, and native S3 lockfiles. The helper refuses the former ad-hoc AWS CLI bucket path and migrates the bootstrap root's initial local state into its protected backend.

`terraform/scripts/deploy.sh` now follows an online-safe sequence:

1. formatting, backend, and native validation;
2. KMS/ECR availability and immutable image publication;
3. targeted provisioning of the dedicated migration task and dependencies;
4. backward-compatible database migration while the current API/worker revision remains online;
5. full rolling Terraform apply only after migration success;
6. static asset publication and CloudFront invalidation.

Schema changes must therefore remain backward compatible with both the old and new application revisions during the deployment window.

## Required production inputs

The checked-in production values intentionally fail the readiness gate until real deployment facts are supplied:

- non-fake payment provider and valid Stripe/provider credentials;
- custom public domain and Route 53 hosted-zone ID, or approved existing viewer and origin certificate ARNs;
- confirmed operational alarm email or another on-call endpoint;
- SES production access and verified DNS ownership;
- initial account-foundation apply, protected GitHub `dev`/`prod` environments, and dedicated plan/apply role secrets;
- secure AWS credentials for that first bootstrap;
- generated and reviewed `.terraform.lock.hcl` files for all three Terraform roots, using `./terraform/scripts/update-provider-locks.sh`.

These values cannot be invented safely by Terraform and should not be committed as secrets.

## Deferred architecture layers—not missing module controls

The following are deliberately outside a single workload repository and should be implemented when the corresponding organizational boundary exists:

- AWS Organizations delegated GuardDuty/Security Hub/Config administration;
- centralized cross-account immutable log archive;
- cross-region application and database disaster recovery;
- organization-wide SCPs and centrally governed organization-level permission boundaries beyond this repository-level workload boundary;
- SaaS-provider credential rotation automation;
- production incident paging, ticketing, and restore-drill evidence.

## Provider dependency lock status

The repository intentionally does not fabricate provider lock files. Generate signed, multi-platform lock files from an internet-connected trusted environment before production:

```bash
./terraform/scripts/update-provider-locks.sh
```

Commit the resulting `.terraform.lock.hcl` file from the workload, bootstrap, and account roots. See [`TERRAFORM_PROVIDER_LOCKS.md`](TERRAFORM_PROVIDER_LOCKS.md).

## Validation commands

```bash
python scripts/validate_terraform_module_contracts.py
python scripts/validate_security_remediation.py
python scripts/validate_workflows.py
python scripts/static_checks.py
python scripts/validate_documentation_links.py

cd terraform/tests
go vet ./...
go test -race -count=1 ./...
```

GitHub Actions additionally runs native Terraform formatting, initialization, validation for all three Terraform roots, TFLint, Checkov, and an AWS-backed development plan.
