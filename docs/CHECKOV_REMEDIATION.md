# Checkov and CI security remediation report

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)  
> **Date:** July 31, 2026

## Executive summary

GitHub Actions run `30634658309` exposed two independent problems: the strict Checkov job detected AWS infrastructure weaknesses, and the npm job stopped before producing `npm-audit.json` because the repository did not yet contain `frontend/package-lock.json`. This remediation changes the underlying Terraform resources, preserves a strict blocking gate, and guarantees a diagnostic npm artifact even when dependency resolution fails.

The project now includes a dependency-free control validator at `scripts/validate_security_remediation.py`. It protects the security-critical Terraform settings and documented exceptions before the full Checkov scan runs. The validator discovers the security workflow by an optional `SECURITY_WORKFLOW_PATH`, the conventional filename, or required workflow content, so renaming or consolidating the workflow cannot produce a `FileNotFoundError`. The validator does not replace Checkov, Terraform validation, TFLint, or an AWS plan.

## Reported Checkov findings and resolution

| Check | Affected resource | Resolution |
|---|---|---|
| `CKV_AWS_150` | Application Load Balancer | `enable_deletion_protection` is enabled by default and wired to the environment safety variable. |
| `CKV_AWS_91` | Application Load Balancer | ALB access logging writes to the centralized private S3 audit-log bucket. |
| `CKV_AWS_2` | ALB listener | Custom-domain deployments redirect HTTP to HTTPS and use a TLS 1.2/1.3 listener. The certificate-less development origin is restricted to CloudFront origin-facing IP ranges and has a narrowly documented exception. |
| `CKV_AWS_86` | CloudFront distribution | CloudFront standard access logging writes to the centralized audit-log bucket. |
| `CKV_AWS_310` | CloudFront distribution | A documented architecture exception explains that API failover requires a separately deployed secondary application stack; the static S3 origin cannot safely impersonate an API failover target. |
| `CKV_AWS_374` | CloudFront distribution | A documented product exception preserves worldwide access for fans, bands, organizers, venues, and sponsors; WAF and rate limiting provide compensating controls. |
| `CKV_AWS_300` | CloudTrail log bucket | The lifecycle rule aborts incomplete multipart uploads after seven days. |
| `CKV_AWS_252` | CloudTrail | CloudTrail publishes delivery notifications to an encrypted SNS topic with an explicit service policy. |
| `CKV_AWS_26` | SNS topics | CloudTrail and operational-alert topics use the environment customer-managed KMS key and deny insecure transport. |
| `CKV_AWS_338` | ECS and application log groups | ECS Exec, API, worker, and migration logs retain data for at least 365 days; variable validation prevents shorter values. |
| `CKV_AWS_297` | EventBridge Scheduler | Scheduler metadata is encrypted with the customer-managed KMS key, and the scheduler role has only the SQS/KMS permissions it needs. |
| `CKV_AWS_109` | KMS key policy | Account administration and cryptographic service access are constrained by exact principals and context conditions. |
| `CKV_AWS_111` | KMS key policy | Restrictable actions use exact resources; only AWS APIs or key-policy semantics that cannot be resource-scoped use `Resource = "*"`. |
| `CKV_AWS_356` | KMS key policy | Inline documentation explains AWS's attached-key-policy self-key semantics and the exact principal/context boundaries around the required wildcard. |
| `CKV_AWS_130` | Public subnets | `map_public_ip_on_launch` is disabled. Public endpoints receive addresses through managed services rather than automatic instance ENI assignment. |
| `CKV_AWS_157` | RDS PostgreSQL | Multi-AZ is enabled by default and is enforced by the production-safety check. |

## Additional infrastructure hardening

### Central audit-log storage

The new `access_logs` module provides a single private destination for ALB, CloudFront, S3 server-access, and CloudTrail bucket-access records. It enables versioning, TLS-only access, public-access blocking, seven-day abandoned-upload cleanup, Glacier Instant Retrieval transition, and configurable retention. It intentionally uses SSE-S3 because ALB and legacy CloudFront standard log delivery do not consistently support a customer-managed KMS destination. The bucket ACL explicitly preserves full control for the bucket owner and AWS's documented CloudFront `awslogsdelivery` canonical user, preventing a later Terraform apply from removing the grant required for legacy CloudFront log delivery.

### Network boundaries

- The VPC default security group has no ingress or egress rules.
- ALB ingress is limited to AWS's CloudFront origin-facing managed prefix list.
- ALB egress is limited to the application port inside the VPC.
- Application tasks can reach HTTPS externally and only the required database, Redis, and DNS ports internally.
- Database and Redis groups accept traffic only from the application security group and use port-restricted VPC egress.
- Public subnets do not assign public IP addresses automatically.
- VPC flow logs are KMS encrypted and retained for at least one year.

### Database and cache

- PostgreSQL uses KMS encryption, enforced TLS, Multi-AZ by default, deletion protection by default, 30-day backups, final snapshots, enhanced monitoring, IAM database authentication capability, and 731-day Performance Insights retention.
- RDS Proxy requires TLS and reads credentials from Secrets Manager.
- Redis uses encryption at rest and in transit, a generated 64-character authentication token, Multi-AZ automatic failover with at least one required replica, snapshots, maintenance windows, and a protected `rediss://` runtime secret.

### Messaging, scheduling, and backups

- Task and dead-letter queues use the customer-managed KMS key, TLS-only policies, long polling, a 14-day DLQ retention period, and source-restricted redrive.
- EventBridge Scheduler encrypts schedule state, uses constrained SQS/KMS IAM, retries failed delivery, and sends terminal failures to the DLQ.
- AWS Backup uses a KMS-encrypted vault, Vault Lock, a 365-day minimum retention baseline, cold-storage transition, and KMS permissions constrained to the exact key. `kms:CreateGrant` is limited by `kms:GrantIsForAWSResource=true`.

### Edge, audit, and detection

- WAF uses AWS managed common and known-bad-input rules plus per-IP rate limiting.
- Full WAF request logs are KMS encrypted, retained at least 365 days, and redact `Authorization` and `Cookie` headers.
- CloudTrail is multi-region, validates log files, uses KMS encryption, and sends encrypted SNS delivery notifications.
- S3 source buckets deliver access logs centrally and abort abandoned multipart uploads.

## Documented exceptions

Suppressions are not used to hide remediable findings. Each exception must satisfy all four rules:

1. The AWS API or product architecture makes the flagged construct unavoidable or intentionally required.
2. The risk is bounded by technical compensating controls.
3. The exact reason appears **inside the governed Terraform resource or data block**, which is where Checkov recognizes inline suppressions.
4. `scripts/validate_security_remediation.py` rejects empty or generic exception reasons.

Current exception categories are limited to:

- Attached KMS key policies, where AWS defines `Resource = "*"` as the key being created.
- AWS APIs such as `ecr:GetAuthorizationToken`, `ssmmessages`, and X-Ray ingestion that do not support resource-level ARNs.
- Globally accessible CloudFront delivery and separately owned multi-region failover.
- Terminal S3 logging destinations, where self-logging would recurse.
- Organization-owned disaster-recovery replication and external-provider credential rotation workflows.

## npm audit failure-path remediation

The frontend audit job now supports both repository states:

- With `frontend/package-lock.json`, it runs `npm ci` against the committed dependency tree.
- Without a lockfile, it generates temporary metadata with `npm install --package-lock-only`, uploads the generated lockfile when possible, and clearly warns that reproducibility is reduced.

Dependency resolution is captured rather than allowed to terminate the job before reporting. When resolution fails, the workflow writes a valid `npm-audit.json` document containing `DEPENDENCY_RESOLUTION_FAILED`, uploads it with `if-no-files-found: error`, and then fails the enforcement step. A successful resolution proceeds to the high/critical production dependency audit.

## GitHub run #24 follow-up

The later workflow run exposed two implementation defects in the first remediation package:

1. The validator hard-coded `.github/workflows/security.yml`, although the repository had consolidated or renamed the security workflow. The validator now performs deterministic discovery and supports the `SECURITY_WORKFLOW_PATH` override.
2. Checkov exception comments were outside Terraform definition scopes. They have been moved inside the exact resource or data block they govern, matching Checkov's supported syntax.

The follow-up also adds real controls for the remaining graph findings: CloudTrail delivery to an encrypted 365-day CloudWatch log group, an explicit bootstrap KMS key policy, mandatory Redis replicas with Multi-AZ automatic failover, and a dedicated REGIONAL WAF association on the ALB. Architecture-specific findings retain narrowly documented in-scope exceptions only where the control is owned by another account/layer or conflicts with an AWS service requirement.

## Validation commands

```bash
python scripts/static_checks.py
python scripts/validate_workflows.py
python scripts/validate_security_remediation.py

find scripts terraform/scripts -type f -name '*.sh' -print0 \
  | xargs -0 -r -n1 bash -n

cd terraform/tests
gofmt -w *.go
go test -race -count=1 ./...
go vet ./...
```

The definitive cloud-independent gate in GitHub additionally runs:

```bash
checkov --directory . \
  --framework terraform cloudformation kubernetes helm bicep arm serverless dockerfile github_actions openapi secrets \
  --enable-secret-scan-all-files
```

Native `terraform fmt`, `terraform init -backend=false`, `terraform validate`, TFLint, and an AWS-backed plan remain necessary because a dependency-free text validator cannot evaluate provider schemas or live account constraints.

## Validation evidence

The final offline evidence bundle is stored in [`../validation/security-remediation-2026-07-31/`](../validation/security-remediation-2026-07-31/). It includes the 100-check remediation validator, Terraform module-contract checks, five-workflow parsing/policy validation, 29 race-enabled Go tests, shell/Python checks, PDF preflight, and documentation-link validation. Native Checkov and Terraform provider-schema checks remain blocking in GitHub Actions because those tools and provider downloads were unavailable in the sandbox.
