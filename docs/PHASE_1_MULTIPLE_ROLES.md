# Phase 1 — Multiple roles and role verification

This phase extends the existing user profile without removing the legacy `GigUserProfile.account_type` field.

## Role catalog

Stable role codes:

- `fan`
- `artist`
- `venue`
- `organizer`
- `sponsor`
- `vendor`
- `equipment_rental`
- `administrator`

Every new user receives a verified `fan` assignment. Existing profile values are backfilled into independent `UserRole` records while preserving `account_type` for compatibility.

## Security decisions

- Authenticated users may request multiple non-administrator roles.
- Professional role requests start as `pending`.
- Users cannot request the `administrator` role.
- Users cannot verify or reject their own role assignments.
- Only Django staff or a previously verified administrator role may review another user's request.
- Every request, resubmission, verification, and rejection creates an append-only `RoleAuditEvent`.

## API

- `GET /api/auth/roles/` — available roles, current assignments, and administrator review queue when authorized.
- `POST /api/auth/roles/` — request or update a non-administrator role.
- `POST /api/auth/roles/<id>/verify/` — administrator verification.
- `POST /api/auth/roles/<id>/reject/` — administrator rejection.

## Validation

The phase must pass the complete backend suite, the 90% coverage gate, empty-database migrations, strict `npm ci`, the production frontend build, security checks, and Terraform static validation. No Terraform deployment job is permitted.

## Scope boundary

Campaign submission and administrator campaign approval are intentionally deferred to Phase 1B. No Terraform or deployment behavior is changed by this phase.
