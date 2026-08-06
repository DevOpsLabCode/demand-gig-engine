# Phase 1B — Deterministic Campaign Approval

## Goal

Campaign owners cannot directly approve or launch their own draft campaigns. Submission runs a deterministic, testable ruleset. Passing campaigns are automatically approved. Failed checks create an immutable review record and route the campaign to an administrator queue.

No AI model decides approval.

## Lifecycle

```text
draft
  ├─ automatic checks pass → approved → collecting
  └─ automatic checks fail → pending_review
                                  ├─ administrator approves → approved
                                  └─ administrator rejects → rejected → owner edits → resubmits
```

Existing `collecting` campaigns are not changed by the migration.

## Automatic checks

1. Authenticated owner exists.
2. Owner has a verified `organizer` or `administrator` role, or is Django staff.
3. Required campaign and organizer fields are complete.
4. Deadline is in the future.
5. Campaign target and monetary rules pass model validation.
6. No pledge or sponsorship was accepted before approval.

Each result is stored in `CampaignReview.checks`. A failed result is not silently overridden. It becomes `pending_review` with the failed conditions recorded.

## API

```text
GET|POST /api/campaigns/
GET|PUT|PATCH|DELETE /api/campaigns/<slug>/
POST /api/campaigns/<slug>/submit-review/
POST /api/campaigns/<slug>/approve/
POST /api/campaigns/<slug>/reject/
POST /api/campaigns/<slug>/launch/
GET /api/campaigns/review-queue/
```

Administrator rejection requires written notes. Campaign owners may not manually approve or reject their own campaigns, even when they are staff. They may still receive deterministic automatic approval when every published rule passes.

## Audit

Every automatic or manual decision creates:

- An immutable `CampaignReview`
- A matching immutable `CampaignEvent`
- Previous and resulting status
- Reviewer identity for manual decisions
- Written notes
- Structured automatic-check results

## Rollback

Reversing migration `0007_campaign_review` maps `pending_review`, `approved`, and `rejected` campaigns back to `draft` before deleting review records. Existing collecting campaigns remain unchanged.

## Validation commands

```bash
python -m pytest
python -m coverage report
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
npm ci --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

Terraform is unchanged in Phase 1B.
