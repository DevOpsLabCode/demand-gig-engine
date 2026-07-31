# Application online verification

**Project:** Demand Gig Engine  
**Audit date:** July 31, 2026  
**Scope:** Django/React startup path and the Terraform AWS deployment framework

## Result

The packaged code now has a dependency-gated deployment sequence designed to bring the application online in this order:

1. Bootstrap encrypted/versioned S3 Terraform state with native lockfiles.
2. Create KMS and immutable ECR repositories.
3. Build and push backend/frontend images.
4. Provision AWS infrastructure with API and worker desired counts set to zero.
5. Merge a complete provider-secret schema into Secrets Manager.
6. Wait for the RDS Proxy target to report `AVAILABLE`.
7. Run a dedicated one-off Django migration task and require exit code `0`.
8. Scale the API and worker services to environment values.
9. Publish React assets to private S3 and invalidate CloudFront.
10. Retry public smoke checks for readiness, social-auth configuration, the SPA, Django admin, and admin static assets.

The executable offline suites pass. A real AWS plan/apply remains the final authority because provider schemas, account quotas, domain ownership, external OAuth applications, Docker builds, and AWS runtime behavior cannot be fully simulated in this sandbox.

## Startup protections verified

- `/api/health/live/` checks the Django process without taking a healthy task down for a transient dependency outage.
- `/api/health/ready/` checks both PostgreSQL and Redis and is used by ALB and deployment smoke tests.
- PostgreSQL connections explicitly map `sslmode=require` into Django/psycopg options and enable connection health checks.
- RDS Proxy is required to report an available target before migrations start.
- The migration task is separate from the web service and has no web health check.
- ECS services are created at zero capacity until migrations complete.
- Deployment circuit breakers and ALB health checks protect service rollouts.
- CloudFront is the public entry point; the ALB requires both CloudFront origin-facing IP space and a private origin-verification header.
- Only one CloudFront managed-prefix-list ingress rule is used, avoiding the default security-group rule quota problem.
- Viewer and origin ACM certificates are separated by region.
- `/api*`, `/accounts*`, `/admin*`, `/share*`, and `/static*` route to Django; frontend SPA paths route to private S3.
- Django canonicalizes public scheme and host for OAuth/CSRF while CloudFront deliberately does not forward the viewer Host header to the ALB origin.
- Provider credentials are merged into a complete JSON schema before ECS starts, preventing missing secret-key references from stopping tasks.
- The backend and frontend containers use non-root runtime users; the ECS application filesystem is read-only with an explicitly writable `/tmp` volume.
- ECS Exec is disabled by default because it is incompatible with a read-only root filesystem.

## Executed checks

- 69 repository structural checks.
- 76 Terraform files passed offline lexical validation.
- 29 root module instances matched child-module variables and outputs.
- 31 Go contract/orchestration tests passed with the race detector.
- `go vet` passed.
- Five GitHub Actions workflows validated.
- All shell scripts passed `bash -n`.
- Python source compilation passed.
- Django database URL/TLS parsing contract passed.
- 13 TypeScript/TSX files passed syntax parsing.
- Two VibesMeet unit tests and 41 VibesMeet pytest cases passed.
- Credential-pattern scanning passed with zero findings.

## Required production prerequisites

The deployment is non-interactive **after** these account/provider prerequisites exist:

- AWS credentials or a protected GitHub environment with `AWS_TERRAFORM_ROLE_ARN`.
- Sufficient AWS service quotas and permissions.
- A Route 53 domain/hosted zone for a stable production hostname, or acceptance of the generated CloudFront hostname.
- OAuth applications created and approved by Google/Meta/TikTok, with the deployed callback URLs registered.
- A private provider-credentials JSON file based on `terraform/envs/provider-credentials.example.json`.
- SES production access when real outbound email is required.

External provider registration and approval cannot be performed by Terraform without access to those provider accounts.

## Commands

```bash
./terraform/scripts/validate.sh

cd terraform/tests
go test -race -count=1 -v ./...
go vet ./...
```

After AWS authentication and provider prerequisites:

```bash
PROVIDER_CREDENTIALS_FILE=/secure/provider-credentials.json \
  ./terraform/scripts/deploy.sh dev
```
