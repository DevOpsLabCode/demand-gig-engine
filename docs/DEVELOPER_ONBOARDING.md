# Developer Onboarding - Demand Gig Engine

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Goal

This guide takes a new contributor from an empty workstation to a safe, reviewable change. It explains what to run, where behavior lives, and how to avoid bypassing domain, security, or infrastructure controls.

## 1. Understand the architecture before editing

The frontend never changes campaign state directly. It sends JSON to Django. A view authenticates and authorizes the caller, a serializer validates untrusted data, and a service function performs the transaction. Models define durable state and database constraints. External systems are reached through adapters so tests can replace them with fakes.

```text
React component
  -> frontend/src/api.ts
  -> backend/gigs/urls.py
  -> backend/gigs/views.py
  -> backend/gigs/serializers.py
  -> backend/gigs/services.py
  -> backend/gigs/models.py
  -> payment / Meta / VibesMeet adapter
```

Read [`CODE_WALKTHROUGH.md`](CODE_WALKTHROUGH.md) for every file and named code block.

## 2. Local prerequisites

- Python 3.11 or a compatible supported release
- Node.js and npm compatible with the current Vite toolchain
- PostgreSQL for a production-like local database, or the database supplied by Docker Compose
- Docker and Docker Compose for the simplest full-stack startup
- Terraform 1.x, AWS CLI v2, Go, TFLint, and Checkov for infrastructure work

## 3. Start with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The default local endpoints are:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/`
- Health check: `http://localhost:8000/api/health/`

Use only local/test credentials. Never place production secrets in `.env`, screenshots, test fixtures, command history, or committed `.tfvars` files.

## 4. Run the complete validation entry point

```bash
./scripts/run_all_tests.sh
```

The command coordinates structural checks, workflow validation, Django checks, migrations, blocking Flake8 rules, pytest coverage, frontend compilation, Compose validation, and security scans when their tools are installed.

For quick dependency-free checks:

```bash
python scripts/static_checks.py
python scripts/validate_workflows.py
python -m compileall -q backend scripts
find scripts terraform/scripts -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

For Terraform contracts:

```bash
cd terraform/tests
go test -race -count=1 -v ./...
go vet ./...
```

## 5. Make backend changes safely

1. Add or update model constraints first when the rule must remain true regardless of caller.
2. Put cross-object lifecycle behavior in `services.py`, not in the React component or view.
3. Use `transaction.atomic()` and row locking for state transitions affected by concurrent requests.
4. Validate all incoming fields in serializers.
5. Keep authorization in permissions and action-specific checks.
6. Wrap external network behavior behind payment, Meta, or VibesMeet adapters.
7. Add success, rejection, idempotency, retry, and permission tests.

## 6. Make frontend changes safely

1. Update shared types in `frontend/src/types.ts`.
2. Add or update a typed request function in `frontend/src/api.ts`.
3. Keep provider SDK details in `facebook.ts`, `meta.ts`, or `stripe.ts`.
4. Treat API errors as user-visible state; do not silently discard them.
5. Verify desktop and mobile layouts and preserve keyboard-accessible controls.
6. Run `npm run build` before submitting the change.

## 7. Make Terraform changes safely

1. Change the smallest reusable module that owns the resource.
2. Add variables only when callers genuinely need a choice; prefer secure defaults.
3. Return outputs only when another module or deployment operation needs them.
4. Update module README tables and the architecture document when interfaces change.
5. Extend Go contract tests for every important security, availability, routing, or orchestration invariant.
6. Review the plan for public access, IAM expansion, encryption changes, resource replacement, and deletion.

```bash
./terraform/scripts/validate.sh
```

## 8. Pull-request checklist

- The code explains **why**, not merely what the syntax says.
- No secret, token, private key, customer data, or personal data is committed.
- New state transitions are transactional and idempotent where retries are possible.
- Tests cover happy paths and failure paths.
- Coverage remains at or above the documented 90% line and branch threshold.
- Workflows use pinned, approved action versions and least-privilege permissions.
- Terraform documentation, examples, and outputs match the actual module contract.
- `README.md`, security documentation, and reports are updated when behavior changes.

## 9. Common debugging path

- **Frontend cannot load data:** inspect the browser network request and `frontend/src/api.ts` base URL.
- **401/403 response:** check authentication state, object ownership, staff status, CSRF, and provider configuration.
- **400 response:** inspect serializer errors; do not bypass validation in the view.
- **Campaign state error:** read the current status and the allowed transition in `services.py`.
- **Duplicate pledge/payment:** verify campaign-scoped idempotency keys and provider idempotency headers.
- **Webhook rejected:** verify raw-body signature, timestamp policy, configured secret, and event schema.
- **Terraform plan fails:** validate module input names, provider aliases, region requirements, and remote-state bootstrap.

## 10. Definition of done

A change is complete only when the implementation, inline explanations, automated tests, security checks, public documentation, and operational instructions all describe the same behavior.
