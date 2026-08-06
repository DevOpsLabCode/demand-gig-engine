# Phase 2 — Campaign date, price, and attendance preferences

## Summary

Phase 2 adds transparent demand voting to the existing Django and React application without introducing a worker or a separate service.

Campaign owners can define multiple proposed dates and ticket-price choices while a campaign is still draft or rejected. Signed-in supporters can create or update one preference per campaign after approval. Public campaign payloads expose aggregate demand only.

## Data model

### CampaignDateOption

- Campaign
- Start and end date/time
- Venue time zone
- Public label
- Active state

The end time must be after the start time.

### CampaignPriceOption

- Campaign
- Decimal amount
- Three-character currency
- Public label
- Active state

Amounts are nonnegative and currency values are normalized to uppercase.

### SupporterPreference

- Campaign
- Authenticated user
- Expected ticket quantity
- Physical or virtual attendance
- Selected date option
- Selected ticket-price option
- Preferred neighborhood
- Accessibility notes
- Referral source
- Created and updated timestamps

A database uniqueness constraint enforces one record per campaign and user. Updates replace the existing preference rather than creating duplicate votes.

## Voting rules

Voting is accepted only for approved or active campaign states. It is blocked for draft, pending-review, rejected, expired, cancelled, failed, refund, and completed states.

Selected options must:

- Belong to the same campaign
- Be active
- Remain internally consistent with the campaign

Campaign owners, Django staff, and verified administrators can manage options. Date and price options may be changed only while the campaign is draft or rejected, preventing silent changes after supporters vote.

## Aggregate calculations

The public summary keeps these values separate:

- Supporter preference count
- Expected attendance
- Physical expected attendance
- Virtual expected attendance
- Projected ticket revenue
- Deposits collected
- Sponsor commitments
- Total conditional funding

Projected ticket revenue is calculated as:

```text
sum(expected quantity × selected ticket price)
```

Total conditional funding contains only collected supporter deposits plus active sponsor commitments. It does not include projected ticket revenue.

Date and price results include option totals and percentages, but never voter usernames, emails, neighborhood choices, referral sources, or accessibility notes.

## Campaign visibility

Anonymous visitors can list and retrieve approved or active campaigns. Draft, pending-review, rejected, expired, cancelled, and other private lifecycle states remain visible only to their owner or a trusted campaign reviewer.

## API

### Campaign creation and editing

`POST /api/campaigns/` and protected campaign updates accept optional nested:

- `date_options`
- `price_options`

Nested writes occur in the same database transaction as the campaign write.

### Date options

- `GET|POST /api/campaigns/<slug>/date-options/`
- `GET|PUT|PATCH|DELETE /api/campaigns/<slug>/date-options/<id>/`

### Price options

- `GET|POST /api/campaigns/<slug>/price-options/`
- `GET|PUT|PATCH|DELETE /api/campaigns/<slug>/price-options/<id>/`

### Supporter preference

- `GET|POST|PUT|PATCH /api/campaigns/<slug>/preference/`

GET returns only the authenticated user's own preference.

### Public aggregate

- `GET /api/campaigns/<slug>/preference-summary/`

The aggregate is safe for anonymous access when the campaign is public.

## Frontend

The React campaign creation form supports multiple date and price rows. Campaign cards display voting summaries and separate financial metrics. Signed-in supporters can select attendance mode, expected quantity, date, ticket price, neighborhood, accessibility notes, and referral source, then update the same preference later.

## Security decisions

- Authentication is required for voting.
- Campaign option mutation requires owner or administrator authority.
- Database transactions protect option replacement and preference upsert.
- Cross-campaign and inactive option IDs are rejected.
- Public APIs expose aggregate results only.
- Private accessibility and referral information remains attached to the supporter's own record.
- Decimal arithmetic is used for projected revenue and financial totals.
- Significant option and preference changes create immutable campaign audit events.
- Static API errors avoid exposing internal exception details.

## Migration and rollback

Migration `gigs.0008_campaign_preferences` creates the three Phase 2 tables, indexes, uniqueness constraints, and quantity/amount/date-order checks.

Rollback drops Phase 2 preference data and option records. Existing campaigns, pledges, sponsor commitments, approval reviews, and lifecycle records are not modified.

## Infrastructure status

No Terraform, Docker, GitHub Actions workflow, payment-provider, or deployment files are changed by Phase 2.

## Exact next pull request

Phase 3: Artist interest and verified artist-response workflow.
