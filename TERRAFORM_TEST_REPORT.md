# Terraform framework and application-online test report

**Project:** Demand Gig Engine  
**Validation date:** July 31, 2026  
**Framework:** modular AWS development and production stacks in `terraform/`

## Executive result

The second clean-room audit focused on whether the Django/React application can actually reach and remain in a healthy state after AWS provisioning. The final tree contains **24 reusable AWS modules**, **76 Terraform files**, **29 root module instances**, and **31 Go tests**. Every executable offline check passed, including Go race testing and a mocked deployment that verifies state bootstrap, ECR publication, zero-capacity provisioning, RDS Proxy readiness, one-off migrations, ECS scale-up, static publication, CloudFront invalidation, and public smoke checks.

A successful offline contract suite is not equivalent to a real AWS deployment. Native Terraform provider-schema validation, Docker image builds, AWS planning/applying, account quota checks, and external OAuth approvals still run in GitHub/AWS and remain required before production release.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Repository validation | PASS | 69 checks, 0 failures |
| Terraform lexical scan | PASS | 76 `.tf` files |
| Root/module interfaces | PASS | 29 module instances; no unknown/missing inputs or outputs |
| Go suite | PASS | 31 tests |
| Go race detector | PASS | `go test -race -count=1 -v ./...` |
| Go static analysis | PASS | `go vet ./...` |
| Mock remote-state bootstrap | PASS | Encryption, versioning, public block, TLS policy, native lockfile |
| Mock deployment orchestration | PASS | Build/push, zero capacity, proxy wait, migration, scale-up, S3 sync, invalidation, smoke checks |
| Shell syntax | PASS | All repository shell scripts |
| Python compilation | PASS | Backend and scripts |
| Database TLS settings | PASS | `sslmode=require` mapped to psycopg options; connection health checks enabled |
| Workflow validation | PASS | Five GitHub Actions workflows |
| TypeScript/TSX parsing | PASS | 13 source files |
| VibesMeet unit tests | PASS | 2 tests |
| VibesMeet pytest suite | PASS | 41 cases |
| Credential-pattern scan | PASS | Zero credential/private-key findings |

## Material launch defects fixed in the second audit

1. Added separate liveness and dependency-aware readiness endpoints.
2. Changed ALB health checks and deployment gating to the readiness endpoint.
3. Wait for the RDS Proxy target to become `AVAILABLE` before migrations.
4. Explicitly map PostgreSQL `sslmode=require` into Django database options.
5. Added persistent-connection health checks for recycled RDS Proxy connections.
6. Added a dedicated migration task and require its named container to exit `0` before service scale-up.
7. Prevent missing provider-secret keys from stopping ECS tasks by merging supplied values into a complete secret schema.
8. Added a private CloudFront-to-ALB verification header in addition to the AWS-managed CloudFront prefix list.
9. Limited the ALB to one origin port so the CloudFront prefix list does not exceed default security-group quotas.
10. Separated the `us-east-1` CloudFront viewer certificate from the regional ALB origin certificate.
11. Stopped forwarding the viewer Host header to the HTTPS ALB origin and canonicalized the public URL inside Django.
12. Routed Django admin/Allauth `/static*` assets to WhiteNoise instead of the React S3 origin.
13. Removed distribution-wide SPA error rewriting that could convert API errors into HTML.
14. Added non-root containers, read-only application filesystems, and an explicitly writable `/tmp` volume.
15. Disabled ECS Exec by default to preserve read-only-root security.
16. Added public smoke tests for readiness, auth configuration, SPA, admin login, and admin CSS.
17. Restricted GitHub OIDC trust to matching protected environments.
18. Removed an unused ECR input from the GitHub OIDC module.

## Deferred native/runtime checks

| Check | Reason not executed here | Required execution location |
|---|---|---|
| `terraform fmt/init/validate` | Terraform binary/provider plugins unavailable in sandbox | `.github/workflows/terraform.yml` |
| TFLint and Checkov | External tooling unavailable | Terraform/security workflows |
| Docker backend/frontend builds | Docker daemon unavailable | GitHub/deployment runner |
| Complete Django/Allauth suite | Sandbox package mirror lacks required distributions | Application test matrix |
| Complete Vite build | Sandbox npm mirror lacks Stripe packages | Frontend build job |
| AWS plan/apply | No AWS credentials/account/domain | Protected GitHub environment |
| Live OAuth login | Requires provider applications, approvals, and callback registration | Deployed environment |

## Reproduce

```bash
./terraform/scripts/validate.sh

cd terraform/tests
go test -race -count=1 -v ./...
go vet ./...
```

For deployment after AWS/provider prerequisites:

```bash
PROVIDER_CREDENTIALS_FILE=/secure/provider-credentials.json \
  ./terraform/scripts/deploy.sh dev
```

See [`APPLICATION_ONLINE_VERIFICATION.md`](APPLICATION_ONLINE_VERIFICATION.md) for the startup sequence and production prerequisite checklist.
