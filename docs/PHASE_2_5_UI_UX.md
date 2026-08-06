# Phase 2.5 — UI/UX Comfort and Discovery Redesign

## Purpose

This frontend-only phase makes the Phase 2 workflows feel familiar, calm, and usable before Phase 3 adds artist-response complexity.

No backend, API, database, Terraform, Docker, payment, approval, or security behavior changes are included.

## Design principles

1. **Discovery before administration**
   - Campaign search and filtering are the primary home experience.
   - Organizer and role controls are available without dominating the page.

2. **One dominant action at a time**
   - Campaign lifecycle and user permissions determine the primary call to action.
   - Secondary operations remain available through clear tabs.

3. **Progressive disclosure**
   - Campaign cards start with status, story, progress, audience, and funding.
   - Voting, deposits, sponsorships, approval details, and Facebook tools are separated into focused panels.

4. **Comfortable forms**
   - Campaign creation is divided into four steps:
     1. Basics
     2. Dates and prices
     3. Goal and organizer
     4. Review
   - Supporter voting uses selectable cards, a segmented attendance control, and a quantity stepper.

5. **Accessibility**
   - Visible `:focus-visible` treatment.
   - Minimum practical 44-pixel interactive controls.
   - Semantic progress bars, tabs, fieldsets, legends, status regions, and labels.
   - Reduced-motion support.
   - Responsive single-column layouts and full-width mobile actions.

6. **Financial clarity**
   - Projected ticket revenue remains labeled as a forecast.
   - Deposits and sponsorship commitments remain separate.
   - Voting remains explicitly described as neither payment nor reservation.

## Updated frontend files

- `frontend/src/App.tsx`
- `frontend/src/components/CampaignCard.tsx`
- `frontend/src/components/CreateCampaignForm.tsx`
- `frontend/src/components/SupporterPreferenceForm.tsx`
- `frontend/src/main.tsx`
- `frontend/src/ui-refresh.css`

## Review checklist

- Anonymous visitor can understand the product and discover public campaigns.
- Authenticated user can create a campaign without facing one oversized form.
- Supporter can vote on date, price, quantity, and attendance mode comfortably.
- Organizer sees approval or launch as the dominant action.
- Administrator sees review action only when relevant.
- Funding and sponsorship controls are available without crowding the main card.
- Facebook tools remain available under the secondary tools surface.
- Keyboard focus is always visible.
- Mobile layouts require no horizontal page scrolling.
- No existing Phase 0–2 business logic is removed.
