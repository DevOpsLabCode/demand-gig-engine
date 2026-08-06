# Open Concert Network / Demand Gig Engine — Implementation Agent Plan

**Repository:** `DevOpsLabCode/demand-gig-engine`  
**Product:** Open Concert Network / Demand Gig Engine  
**Owner:** Stan Zvenigorodskiy, DevOps Lab Inc.

## Mission

Extend the existing Django REST Framework, React, TypeScript, PostgreSQL, Docker, and Terraform application into a demand-driven event-production network.

Do not rewrite the repository. Do not replace the current application architecture. Do not introduce Supabase, Cloudflare Workers, Celery, RQ, Kafka, or a new dedicated background worker. Do not remove the existing AWS or worker-ready code. New MVP functionality must not depend on SQS or EventBridge. Do not enable live payments during this work; keep new workflows functional with zero-dollar commitments.

## Mandatory branch and approval controls

1. Never commit directly to `main`.
2. Never merge a pull request automatically.
3. Implement one phase at a time on a feature branch.
4. At the end of every phase, commit and push only to that phase branch.
5. Stop after every phase so Stan can manually run and review Terraform.
6. Do not run Terraform `apply` or `destroy` through this implementation workflow.
7. Continue only after Stan explicitly confirms that the next phase may begin.
8. Do not claim completion while required tests or security gates fail.

## Target workflow

```text
Create user
→ add one or more marketplace roles
→ propose “Bring this artist to this city”
→ submit campaign for administrator review
→ administrator approves campaign
→ publish campaign
→ collect supporter pledges
→ vote on dates and ticket prices
→ measure attendance and projected revenue
→ gather artist availability
→ gather venue soft interest
→ request vendor and equipment quotes
→ gather sponsor interest
→ calculate readiness
→ administrator approves handoff
→ generate VibesMeet handoff record
```

## Engineering rules

- Preserve backward compatibility whenever practical.
- Use database migrations for every schema change.
- Include safe data migrations and rollback considerations.
- Use database transactions for threshold and lifecycle changes.
- Use `Decimal` for monetary calculations.
- Add immutable audit events for significant transitions.
- Public read endpoints must be safe for anonymous access.
- Authentication is required for votes, stakeholder submissions, and campaign changes.
- Owner or administrator permission is required for campaign management.
- Administrator permission is required for approval, rejection, verification, and final handoff.
- Users may not self-verify professional roles or grant themselves administrator access.
- Campaign owners may not silently bypass approval.
- Add tests before or with each feature.
- Maintain at least 90% backend line and branch coverage.
- Run frontend TypeScript validation and the production build.
- Return complete updated files when displaying code.
- Never commit credentials or real personal information.

## Phase 0 — Establish a trustworthy baseline

Branch:

```text
feature/open-concert-mvp-foundation
```

Required validation:

```text
python -m pytest
python -m coverage report
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py migrate --noinput
npm ci --prefix frontend
npm run build --prefix frontend
npm run typecheck --prefix frontend, when configured
```

Confirm registration, login, profile update, campaign creation, campaign launch, zero-dollar pledge, sponsor commitment, public campaign API access, and migration of an empty database.

Do not begin Phase 1 until the application baseline is green. Terraform deployment remains manual and outside the Phase 0 CI workflow.

## Phase 1 — Multiple roles

Create `Role` and `UserRole` models supporting:

```text
fan
artist
venue
organizer
sponsor
vendor
equipment_rental
administrator
```

A user may hold multiple roles. Assign `fan` automatically at registration. Users may request additional roles but may not self-verify or grant themselves administrator. Temporarily retain `GigUserProfile.account_type` and backfill existing values into `UserRole`.

## Phase 1B — Campaign submission and administrator approval

Extend the lifecycle:

```text
draft
pending_review
approved
collecting
threshold_reached
feasibility_review
conditionally_ready
ready
handed_off
confirmed
completed
rejected
expired
cancelled
not_viable
refund_pending
refunded
```

Create `CampaignReview` with reviewer, decision, notes, timestamps, previous status, and resulting status. Owners submit drafts; administrators approve or reject; only approved campaigns enter collecting. Every decision creates an audit event.

## Phase 2 — Date, ticket-price, and attendance voting

Create:

- `CampaignDateOption`
- `CampaignPriceOption`
- `SupporterPreference`

Support one active preference per user per campaign, editable votes, physical or virtual attendance, expected quantity, aggregate date and price results, and projected ticket revenue.

Keep these values separate:

```text
Supporter count
Expected attendance
Projected ticket revenue
Deposits collected
Sponsor commitments
Total conditional funding
```

## Phase 3 — Artist, venue, vendor, and equipment workflows

Add distinct workflows for:

- Artist interest, conditional availability, fees, dates, travel requirements, rider, verification, and expiration.
- Venue interest, conditional holds, capacity, dates, rental cost, bar guarantee, equipment, accessibility, age restrictions, livestream capability, verification, and expiration.
- Vendor profiles, service categories, quote requests, fixed or conditional quotes, in-kind support, revenue share, included equipment, validity, and acceptance controls.

A soft-interest response must never be displayed as confirmed.

## Phase 4 — Sponsor interest

Preserve existing sponsor commitments and add an earlier workflow:

```text
interested
→ discussing
→ proposed
→ committed
→ paid
→ finalized
```

Sponsors may express interest without immediately entering a monetary commitment or payment.

## Phase 5 — Readiness checklist

Create deterministic, testable readiness models and checks for:

```text
campaign_approved
attendance_threshold
projected_revenue_threshold
artist_available
venue_available
budget_complete
required_vendor_coverage
quotes_not_expired
sponsor_requirement
administrator_approval
```

Outcomes:

```text
blocked
not_viable
conditionally_ready
ready
```

AI must not decide readiness. Administrator overrides require a written reason and an audit record.

## Phase 5B — VibesMeet handoff

Create a versioned, immutable `VibesMeetHandoff` snapshot generated from a readiness assessment. Include campaign, artist, venue, proposed date, physical and virtual attendance, ticket-price results, projected revenue, sponsors, vendor quotes, preliminary budget, readiness results, administrator approval, checksum, export timestamps, and remote event status.

First version requirements:

- JSON export
- Printable HTML view
- No live VibesMeet API submission
- Preserve existing `ExternalResourceLink` and webhook models

## Phase 6 — Public campaign experience

Add public routes for campaign discovery, campaign detail, and the pilot map. Require login only for protected actions such as voting, pledging, stakeholder submissions, profile changes, and campaign management.

Preserve tracked Facebook URLs and legacy `?campaign=<slug>` behavior. Never expose supporter email addresses.

## Phase 7 — Greenwich Village pilot map

Use MapLibre directly in the React frontend. Do not use Cloudflare Workers.

Initial viewport:

```text
Bleecker Street
MacDougal Street
West 4th Street
Greenwich Village, New York
```

Marker types:

```text
venue
proposed_campaign
artist
equipment_rental
vendor
sponsor_opportunity
physical_event
hybrid_event
```

Only visible and reviewed records may be public. Unverified entities must be labeled clearly. Include marker filters, an accessible list view, bounding-box API filtering, and authorization tests.

## No-worker operating model

The MVP runs with:

- React frontend
- Django web/API process
- PostgreSQL
- Existing static-file approach
- Existing Docker configuration

Reuse `manage.py expire_campaigns` through a hosting scheduler or system cron. Do not add a continuously running worker and do not expose an unauthenticated expiration endpoint.

## Pull-request sequence

1. Baseline, CI, and documentation.
2. Multiple roles and role verification.
3. Campaign submission and administrator approval.
4. Date, price, and attendance voting.
5. Artist, venue, vendor, and equipment responses.
6. Sponsor interest and preliminary budget.
7. Readiness engine and VibesMeet handoff.
8. Public campaign pages and pilot map.
9. End-to-end Greenwich Village demonstration.

## End-of-phase report

Every phase report must include:

- Summary
- Files added
- Files modified
- Migrations
- API changes
- Security decisions
- Tests executed
- Coverage
- Frontend build result
- Terraform status and manual commands for Stan
- Known limitations
- Exact next phase

After reporting, stop. Continue only after Stan explicitly authorizes the next phase.
