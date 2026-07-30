# Demand-Driven Gig Creation MVP

A production-minded reference implementation of the missing Open Concert / VibesMeet workflow:

> **Plant the seed → gather supporters → reach the target → confirm the artist and venue → produce the gig.**

This is not ordinary ticketing. A campaign proves real demand before an organizer assumes the full cost and risk of booking the artist, venue, production, security, insurance, travel, and promotion.

## Product idea

A fan, artist, promoter, venue, sponsor, or community administrator proposes a gig such as:

> **Bring Band X to New York.**

The organizer defines one or both minimum thresholds:

- 500 verified supporters
- $25,000 in refundable commitments and sponsorships

Fans can register their intent, reserve a place, or pay a refundable deposit. Sponsors can commit after seeing verified audience demand. Only after the threshold is reached does the organizer confirm the artist and venue and convert the campaign into a normal ticketed VibesMeet event.

When the threshold is missed or the artist and venue cannot be confirmed under the published terms, deposits are refunded.

---

## Included

### Demand-campaign platform

- Django REST Framework API
- PostgreSQL-ready data model with SQLite fallback
- React + TypeScript + Vite interface
- Supporter attendance commitments
- Refundable supporter deposits
- Sponsor commitments
- Supporter-count, committed-money, or combined thresholds
- Atomic threshold evaluation to prevent race conditions
- Artist and venue confirmation gates
- Conversion into a live VibesMeet event through an `event_id`
- Failed-campaign refund workflow
- Stripe adapter and local fake-payment adapter
- Stripe webhook verification
- Idempotency keys for pledge submissions
- Immutable campaign-event audit log
- Automated tests for success and refund flows
- Docker Compose setup

### Facebook-first organizer integration

- Existing Facebook Event URL attached to every gig seed
- Existing Facebook Group URL attached to every gig seed
- Artist, venue, or organizer Facebook Page URL
- Facebook Share Dialog with campaign-specific links
- Open Graph preview pages optimized for Facebook sharing
- Facebook Login with backend token validation
- Discovery of Facebook Pages managed by the connected organizer
- Publishing a campaign link to a managed Facebook Page
- Unique Group, community, and administrator referral codes
- Attribution of supporters, deposits, and revenue to each Facebook source
- Meta Pixel browser events
- Meta Conversions API server events
- Browser/server event IDs for deduplication
- Website, app, and physical attendance/check-in conversion events
- Facebook source data in the immutable campaign audit log

---

# Facebook integration strategy

## The operating principle

Event organizers already use **Facebook Events, Facebook Groups, Facebook Pages, Messenger, and community discussions** as their primary discovery and promotion channels.

The goal is not to force organizers to abandon those communities. The integration uses Facebook as the audience and communication layer while VibesMeet becomes the transaction, verification, sponsorship, and fulfillment layer.

```text
Facebook Group / Event / Page
        ↓
Tracked “Make This Gig Happen” link
        ↓
VibesMeet demand campaign
        ↓
Verified supporter + refundable commitment
        ↓
Threshold reached
        ↓
Artist + venue confirmed
        ↓
Normal VibesMeet ticketed event
        ↓
Facebook Page/Event promotion + measured attendance
```

## Why full Facebook Group syncing is not implemented

Meta retired the general-purpose Facebook Groups API and its permissions, including `publish_to_groups` and `groups_access_member_info`, for all versions on April 22, 2024.

Therefore, a compliant modern application cannot:

- Import a Facebook Group membership list
- Read private Group member data
- Automatically publish into arbitrary Groups
- Synchronize all Group posts and comments
- Automatically invite every Group member

This project implements the strongest supported alternative:

1. A Group administrator creates a unique tracked link.
2. The administrator manually posts or pins it in the Group or Facebook Event discussion.
3. Facebook generates a rich Open Graph preview.
4. Every visitor carries `source`, `group`, and `ref` attribution into VibesMeet.
5. VibesMeet measures supporters, deposits, sponsorships, conversions, and eventual attendance from that community.

Official Meta reference:

- https://developers.facebook.com/docs/graph-api/changelog/version19.0/

---

# Recommended organizer workflow

## Phase 1 — Plant the seed

The organizer creates the demand campaign and optionally attaches:

- Existing Facebook Event URL
- Main Facebook Group URL
- Artist, venue, or organizer Facebook Page URL
- Minimum supporter target
- Minimum financial target
- Suggested refundable deposit
- Campaign deadline

The Facebook Event can remain the familiar public discussion and discovery hub. The VibesMeet campaign becomes the authoritative place for verified demand.

## Phase 2 — Connect each Facebook community

For each Facebook Group, Event discussion, Page, influencer, artist fan club, or promoter, generate a separate link:

```text
https://your-domain.example/share/campaign/bring-band-x-new-york/
  ?source=facebook_group
  &group=Band%20X%20NYC%20Fans
  &ref=admin-jane
```

Examples:

```text
source=facebook_group&group=Band X NYC Fans&ref=admin-jane
source=facebook_event&group=Official NYC Event&ref=event-discussion
source=facebook_page&group=Band X Official&ref=page-organic
source=facebook_ads&group=NYC Rock Audience&ref=adset-2026-07
source=facebook_messenger&group=Street Team&ref=messenger-captain-4
```

This enables community-level reporting without copying Facebook member data.

## Phase 3 — Share and pin

The organizer should place the tracked campaign URL in:

- Facebook Event ticket or external-link field where available
- Facebook Event description
- Event discussion pinned post
- Facebook Group pinned or featured post
- Facebook Page post
- Messenger community chats
- Artist and venue Page posts
- Relevant comments, with administrator approval
- Meta advertising campaigns

Suggested Facebook post:

```text
Should Band X play New York?

The show is not booked yet. We are proving demand first.

Support the campaign, reserve your place, or leave a refundable deposit. Once the minimum audience and funding target is reached, the artist and venue will be confirmed and the gig will happen.

Make this gig happen:
<TRACKED_CAMPAIGN_LINK>
```

## Phase 4 — Measure demand

Every pledge records:

- `source`
- `source_label`
- `referral_code`
- Supporter count
- Commitment amount
- Payment status
- Campaign and timestamp

Example pledge payload:

```json
{
  "supporter_name": "Alex Fan",
  "supporter_email": "alex@example.com",
  "quantity": 1,
  "amount": "25.00",
  "idempotency_key": "browser-generated-uuid",
  "source": "facebook_group",
  "source_label": "Band X NYC Fans",
  "referral_code": "admin-jane"
}
```

This lets the organizer answer:

- Which Facebook Group produced the most supporters?
- Which Page generated the most deposits?
- Which administrator or promoter has the best conversion rate?
- Which geographic audience should receive the confirmed event announcement?
- Which community should receive a referral fee, recognition, or ticket allocation?

## Phase 5 — Reach the threshold

When the configured minimum is reached, the campaign moves atomically from:

```text
COLLECTING → TARGET_REACHED
```

The organizer then begins artist and venue confirmation. Supporter commitments are not silently treated as final ticket purchases before the published conditions are satisfied.

## Phase 6 — Confirm artist and venue

The campaign records separate confirmation gates:

```text
Artist confirmed: yes/no
Venue confirmed: yes/no
```

Both must be confirmed before the campaign becomes a live event.

Recommended production additions:

- Artist letter of intent
- Venue hold expiration date
- Capacity and accessibility
- Production rider
- Insurance
- Permit requirements
- Cancellation terms
- Deposit conversion terms

## Phase 7 — Convert to the normal VibesMeet event

After artist and venue confirmation:

```text
POST /api/campaigns/<slug>/finalize/
```

The Demand Campaign service publishes `campaign.finalized`. VibesMeet Event OS creates the ordinary confirmed event and returns its `event_id`.

At this point:

- Eligible deposits become final according to campaign terms
- Ticket inventory opens
- The event receives its standard ticketing page
- Facebook Event and Page posts can be updated with the confirmed date, venue, and ticket URL
- SponsorOS receives verified demand and source-attribution data

## Phase 8 — Promote and measure attendance

Use both Meta Pixel and Conversions API to send funnel events such as:

```text
PageView
ViewContent
Lead
InitiateCheckout
Purchase
AttendEvent            # custom physical check-in event
CampaignRefunded       # custom lifecycle event
```

For physical QR check-in, send a server event with:

```json
{
  "event_name": "AttendEvent",
  "event_id": "checkin-vibes-event-123-ticket-456",
  "email": "fan@example.com",
  "action_source": "physical_store",
  "custom_data": {
    "event_id": "vibes-event-123",
    "ticket_id": "ticket-456",
    "venue": "Example Hall"
  }
}
```

API:

```text
POST /api/campaigns/<slug>/facebook/track-conversion/
```

This gives organizers a complete measurement chain from Facebook discovery through real-world attendance.

---

# Facebook integration matrix

| Integration | Implemented | Notes |
|---|---:|---|
| Existing Facebook Event URL | Yes | Stored with the campaign and displayed in the UI |
| Existing Facebook Group URL | Yes | Stored as the principal community hub |
| Facebook Page URL | Yes | Stored for the artist, venue, or organizer |
| Facebook Share Dialog | Yes | Opens a tracked campaign URL |
| Rich Facebook preview | Yes | Dynamic Open Graph page per campaign/source |
| Facebook Login | Yes | JavaScript SDK plus backend token validation |
| Managed Page discovery | Yes | Uses `/me/accounts` after permission approval |
| Publish campaign to Page | Yes | Uses `/{page-id}/feed` |
| Meta Pixel | Yes | Browser PageView and funnel events |
| Meta Conversions API | Yes | Server-side commitment, sponsor, purchase, and custom events |
| Browser/server deduplication | Yes | Shared `event_id` convention |
| Group member import | No | Groups API removed by Meta |
| Automatic arbitrary Group posting | No | Groups API removed by Meta |
| Automatic Group invitations | No | Not available through the current supported API |
| Existing Facebook Event creation/update | Manual workflow | Keep the Event as discovery hub and link it to the VibesMeet campaign |
| Messenger sharing | Link copy/share | Tracked URLs can be pasted into Messenger chats |
| Instagram promotion | Campaign URL | Use the same source/referral model for bio, stories, ads, and DMs |
| WhatsApp promotion | Campaign URL | Use tracked links for chats and communities |
| Offline attendance attribution | Yes | Custom Conversions API event with `physical_store` action source |

---

# Facebook App setup

## 1. Create a Meta app

Create a Meta developer application and add the relevant products:

- Facebook Login
- Marketing API / Conversions API as required by the selected business setup

Official documentation:

- https://developers.facebook.com/docs/facebook-login/web/
- https://developers.facebook.com/documentation/ads-commerce/conversions-api
- https://developers.facebook.com/documentation/meta-pixel

## 2. Configure OAuth

Add the production frontend domain and valid OAuth redirect URIs in the Meta application dashboard.

For local development, the frontend is normally:

```text
http://localhost:5173
```

Production must use HTTPS.

## 3. Request Page permissions

The Page publishing workflow requests:

```text
public_profile
email
pages_show_list
pages_read_engagement
pages_manage_posts
```

Depending on the app mode, organization, users, and intended public use, Meta may require App Review, a screencast, test credentials, business verification, and a clear explanation of how each permission is used.

The production application should request only the permissions actually needed.

Official Page publishing reference:

- https://developers.facebook.com/docs/graph-api/reference/page/feed/

## 4. Configure environment variables

Backend `.env`:

```dotenv
PUBLIC_BASE_URL=https://api.your-domain.example
META_GRAPH_API_VERSION=v25.0
META_APP_ID=your-meta-app-id
META_APP_SECRET=your-meta-app-secret
META_PIXEL_ID=your-pixel-id
META_CONVERSIONS_API_TOKEN=your-system-user-or-dataset-token
META_TEST_EVENT_CODE=
META_DEFAULT_SHARE_IMAGE=https://cdn.your-domain.example/default-gig-share.jpg
```

Frontend `.env`:

```dotenv
VITE_API_BASE=https://api.your-domain.example/api
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...
VITE_META_PIXEL_ID=
```

The frontend normally obtains the Pixel ID and Facebook App ID through:

```text
GET /api/facebook/config/
```

The Meta App Secret and Conversions API token must never be exposed to the browser.

## 5. Configure domains and privacy

Before public release:

- Verify the production domain in Meta Business settings
- Publish privacy and data-deletion instructions
- Explain Facebook Login and advertising measurement in the privacy policy
- Obtain consent where required
- Respect Global Privacy Control and regional consent requirements
- Do not send prohibited or unnecessary personal data
- Hash permitted customer identifiers before sending server events
- Define retention and deletion schedules

---

# Facebook API endpoints

## Read integration configuration

```bash
curl http://localhost:8000/api/facebook/config/
```

## Verify a Facebook Login access token

```bash
curl -X POST http://localhost:8000/api/facebook/login/ \
  -H 'Content-Type: application/json' \
  -d '{"access_token":"USER_ACCESS_TOKEN"}'
```

The backend validates the token against the configured Meta App and then requests the connected user profile.

## List Pages managed by the organizer

```bash
curl -X POST http://localhost:8000/api/facebook/pages/ \
  -H 'Content-Type: application/json' \
  -d '{"access_token":"USER_ACCESS_TOKEN"}'
```

## Generate a Group-specific share link

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/facebook/share-link/ \
  -H 'Content-Type: application/json' \
  -d '{
    "source":"facebook_group",
    "group_name":"Band X NYC Fans",
    "referral_code":"admin-jane"
  }'
```

Response:

```json
{
  "campaign_url": "https://api.example.com/share/campaign/bring-band-x-new-york/?source=facebook_group&group=Band+X+NYC+Fans&ref=admin-jane",
  "share_dialog_url": "https://www.facebook.com/dialog/share?..."
}
```

## Publish to a managed Facebook Page

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/facebook/publish-page/ \
  -H 'Content-Type: application/json' \
  -d '{
    "page_id":"FACEBOOK_PAGE_ID",
    "page_access_token":"PAGE_ACCESS_TOKEN",
    "source":"facebook_page",
    "referral_code":"official-page",
    "message":"Should Band X play New York? Support the seed and help make the gig happen."
  }'
```

The access token is used for the request and is not written into the campaign audit event.

## Send a server or offline conversion

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/facebook/track-conversion/ \
  -H 'Content-Type: application/json' \
  -d '{
    "event_name":"AttendEvent",
    "event_id":"checkin-ticket-456",
    "email":"fan@example.com",
    "action_source":"physical_store",
    "currency":"USD",
    "custom_data":{
      "event_id":"vibes-event-123",
      "ticket_id":"ticket-456"
    }
  }'
```

---

# Open Graph sharing

Facebook should share the backend URL rather than the JavaScript-only frontend URL:

```text
/share/campaign/<slug>/
```

That page contains server-rendered metadata:

```html
<meta property="og:type" content="website">
<meta property="og:title" content="Bring Band X to New York">
<meta property="og:description" content="500 supporters needed...">
<meta property="og:url" content="https://.../share/campaign/bring-band-x-new-york/">
<meta property="og:image" content="https://cdn.../campaign-image.jpg">
```

It also displays a lightweight campaign landing page and routes supporters to the React interface while preserving source, Group, and referral parameters.

Official sharing documentation:

- https://developers.facebook.com/documentation/sharing/web
- https://developers.facebook.com/documentation/sharing/reference/share-dialog/

---

# Meta Pixel and Conversions API

## Browser events

The frontend loads Meta Pixel only when a Pixel ID is configured.

A commitment uses the returned pledge ID as the browser event ID:

```text
pledge:<pledge-uuid>:created
```

## Server events

The backend sends the same event ID to Conversions API, allowing Meta to deduplicate browser and server versions of the event.

Examples:

```text
Lead                     attendance commitment without deposit
InitiateCheckout         refundable deposit initiated/recorded
Purchase                 deposit finalized after gig confirmation
AttendEvent              physical QR check-in
```

The core campaign flow never depends on Meta attribution availability. A Meta API outage must not prevent a supporter from committing, paying, receiving a refund, or entering the event.

## Data minimization

The reference implementation hashes email addresses with SHA-256 before sending them to Conversions API. A production system should additionally handle consent, cookies, `_fbp`, `_fbc`, client IP, user agent, regional restrictions, and data-processing terms in accordance with applicable law and Meta requirements.

---

# Campaign state machine

```text
DRAFT
  ↓ launch
COLLECTING
  ↓ target reached
TARGET_REACHED
  ↓ artist or venue confirmation begins
CONFIRMING
  ↓ both confirmed
CONFIRMED
  ↓ deposits finalized and event created
LIVE
  ↓ event occurs
COMPLETED

COLLECTING + deadline missed → REFUNDING → REFUNDED
Any pre-live cancellation      → REFUNDING → REFUNDED
```

---

# Run with Docker

```bash
cd demand-gig-mvp
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000/api/campaigns/`
- Admin: `http://localhost:8000/admin/`

Create a demo campaign and an admin account:

```bash
docker compose exec backend python manage.py seed_demo
docker compose exec backend python manage.py createsuperuser
```

Apply the Facebook URL migration:

```bash
docker compose exec backend python manage.py migrate
```

# Run without Docker

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

---

# Core API examples

## 1. Plant the seed

```bash
curl -X POST http://localhost:8000/api/campaigns/ \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Bring Band X to New York",
    "pitch":"Prove demand before booking the artist and venue.",
    "artist_name":"Band X",
    "city":"New York",
    "country":"United States",
    "deadline":"2026-09-01T23:59:00-04:00",
    "goal_type":"both",
    "supporter_target":500,
    "amount_target":"25000.00",
    "suggested_deposit":"25.00",
    "currency":"USD",
    "organizer_name":"Open Concert Community",
    "organizer_email":"organizer@example.com",
    "facebook_event_url":"https://www.facebook.com/events/example",
    "facebook_group_url":"https://www.facebook.com/groups/example",
    "facebook_page_url":"https://www.facebook.com/example"
  }'
```

## 2. Launch it

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/launch/ \
  -H 'Content-Type: application/json' -d '{}'
```

## 3. Support it from a Facebook community

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/pledge/ \
  -H 'Content-Type: application/json' \
  -d '{
    "supporter_name":"Alex Fan",
    "supporter_email":"alex@example.com",
    "quantity":1,
    "amount":"25.00",
    "idempotency_key":"browser-generated-uuid",
    "source":"facebook_group",
    "source_label":"Band X NYC Fans",
    "referral_code":"admin-jane"
  }'
```

## 4. Confirm artist and venue

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/confirm-artist/ \
  -H 'Content-Type: application/json' -d '{"details":"Signed artist LOI dated August 20"}'

curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/confirm-venue/ \
  -H 'Content-Type: application/json' -d '{"details":"Venue hold and capacity approved"}'
```

## 5. Convert it into the confirmed event

```bash
curl -X POST http://localhost:8000/api/campaigns/bring-band-x-to-new-york/finalize/ \
  -H 'Content-Type: application/json' -d '{"event_id":"vibesmeet-event-123"}'
```

---

# Stripe configuration

Backend:

```dotenv
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Frontend:

```dotenv
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

Webhook:

```text
/api/payments/stripe/webhook/
```

The implementation charges a refundable deposit rather than calling it escrow. Long campaign periods generally should not depend on card authorization holds. If the target is missed, a refund is issued to the original PaymentIntent.

---

# Suggested VibesMeet integration boundary

Keep demand campaigns as their own bounded context and publish events when state changes occur:

```text
campaign.launched
facebook.share_link_created
facebook.page_post_published
facebook.conversion_forwarded
pledge.created
sponsor.pledged
campaign.target_reached
artist.confirmed
venue.confirmed
campaign.finalized
pledge.refunded
```

VibesMeet Event OS subscribes to `campaign.finalized`, creates the normal ticketed event, and returns the event ID.

SponsorOS consumes:

- Supporter geography
- Facebook source and community attribution
- Verified supporter total
- Verified committed amount
- Sponsor commitments
- Conversion rate by Group/Page/referral code
- Confirmed ticket sales
- QR attendance
- Sponsor impressions and post-event reporting

---


# Testing and validation

Run the dependency-free package checks:

```bash
python scripts/static_checks.py
```

Run the complete backend, frontend, migration, and optional Docker validation in a normal development environment:

```bash
./scripts/run_full_tests.sh
```

The full results, limitations, and corrections made during validation are documented in [`TEST_REPORT.md`](TEST_REPORT.md). The combined README and product screenshots are included at [`docs/Demand_Driven_Gig_MVP_README_and_Screenshots.pdf`](docs/Demand_Driven_Gig_MVP_README_and_Screenshots.pdf).

---

# Production security and hardening

1. Add VibesMeet authentication, role-based authorization, and organizer verification.
2. Protect all Facebook Page and conversion endpoints with organizer/admin permissions.
3. Never persist user or Page access tokens in plaintext.
4. Use encrypted token storage or a secrets vault when long-lived Page access is required.
5. Rotate, revoke, and monitor Meta tokens.
6. Validate that a connected user has the necessary Page task before publishing.
7. Add CSRF, OAuth `state`, nonce, redirect allowlists, and session binding.
8. Run Conversions API events through an idempotent asynchronous queue.
9. Store Meta event IDs and prevent duplicate submissions.
10. Add rate limits to share-link generation, Login verification, Page publishing, and conversion endpoints.
11. Do not allow arbitrary untrusted URLs in Page posts without validation.
12. Add consent management for Pixel and advertising measurement.
13. Add a payout ledger using double-entry accounting.
14. Run refunds asynchronously with retries and dead-letter handling.
15. Add tax, refund, cancellation, chargeback, age, privacy, sanctions, and accessibility rules.
16. Have counsel approve campaign and deposit-conversion terms.
17. Do not claim funds are held in escrow unless a compliant escrow arrangement exists.
18. Add artist and venue contract upload, e-signature, insurance, permit, and capacity workflows.
19. Add fraud controls, velocity limits, bot detection, email verification, and sponsor due diligence.
20. Add metrics, tracing, backups, secret management, security scanning, and incident response.

---

# Important product distinction

Ordinary event platforms work like this:

```text
Book artist and venue → spend money → publish tickets → hope enough people attend
```

This product works like this:

```text
Propose the gig → prove the audience → verify money and sponsors → confirm artist and venue → produce the event
```

That is the core Open Concert concept and the missing demand-validation layer that can sit in front of VibesMeet Event OS and SponsorOS.

---

# Future

> **Status:** This section is the forward-looking product and technical architecture. It preserves the current MVP documentation above and distinguishes capabilities that are implemented today from capabilities proposed for future releases.

## Future product vision

The future platform is an autonomous, demand-driven live-event operating system and multi-sided marketplace.

A single seed such as:

> **Bring Band X to New York.**

can become a complete, traceable event lifecycle:

```text
Plant the seed
    ↓
Create the campaign identity and marketing assets
    ↓
Build a local audience and collect verified support
    ↓
Collect refundable reservations or permitted funding commitments
    ↓
Reach demand and financial thresholds
    ↓
Match the band with available venues, rental suppliers, staff, and sponsors
    ↓
Request standardized quotes and negotiate inside approved limits
    ↓
Sign artist, venue, and supplier agreements
    ↓
Open ticket sales and activate automated marketing
    ↓
Reserve equipment and coordinate production
    ↓
Operate and verify the show
    ↓
Reconcile tickets, refunds, vendors, taxes, and payouts
    ↓
Publish highlights, reports, reviews, and the next campaign
```

The platform is not only a ticket store. It is intended to coordinate demand validation, event creation, marketplace matching, contracts, payments, ticketing, production, marketing, attendance, and settlement.

## Core future principles

1. **Demand before irreversible cost.** Validate audience and purchasing intent before assuming the full risk of a booking.
2. **One event record.** Campaigns, contracts, tickets, venues, rentals, marketing, payments, and settlement share one canonical `event_id`.
3. **One login, multiple account types.** A person can act as a user, band representative, venue manager, organizer, rental supplier, professional, sponsor, or promoter.
4. **Explicit state machines.** Important transitions are deterministic, auditable, and reversible where required.
5. **Rules control money.** AI can recommend actions, but deterministic policy controls budgets, charges, refunds, releases, and capacity.
6. **Autopilot by exception.** Routine work is automated; identity, contracts, safety, compliance, and unusual exceptions receive human review.
7. **The platform is the source of truth.** Facebook, Instagram, YouTube, TikTok, email, and partner sites are distribution channels, not the canonical event database.
8. **No false confirmation.** The platform must not describe a band, date, venue, sponsor, or show as confirmed without the required evidence.
9. **No false escrow claims.** Funds are described according to the actual regulated payment arrangement.
10. **Every material action is attributable.** Important changes produce immutable audit events.

---

# Future account model

## Primary account choices

The first signup screen should present three simple primary choices:

```text
USER
I want to discover, support, propose, and attend events.

BAND
I am a band, artist, manager, booking agent, or authorized representative.

VENUE
I own, operate, or manage an event venue.
```

Additional account types appear under **Business Services**:

```text
EVENT ORGANIZER OR PROMOTER
EQUIPMENT RENTAL COMPANY
EVENT PROFESSIONAL OR SERVICE PROVIDER
SPONSOR
MARKETING AGENCY OR COMMUNITY PARTNER
```

A single authenticated person can create, join, or manage several accounts.

```text
One identity
├── Personal User Account
├── Official Band Account
├── Venue Organization
├── Equipment Rental Company
└── Event Organizer Organization
```

## User account

A User Account serves fans, supporters, event proposers, ticket buyers, ambassadors, volunteers, and attendees.

Users can:

- Create and manage a personal profile
- Follow bands, venues, organizers, and campaigns
- Plant a new event seed
- Support a seed without paying
- Join a refundable reservation campaign
- Save an authorized payment method for a later conditional charge
- Buy, receive, transfer, and refund tickets according to event rules
- Join ticket and campaign waitlists
- Vote on city, date range, venue type, and acceptable price range
- Share tracked referral links
- Earn approved referral rewards or recognition
- Receive event updates through selected channels
- Manage privacy, consent, notification, and marketing preferences
- See upcoming tickets, supported campaigns, refunds, and attendance history

Suggested navigation:

```text
Discover
My Campaigns
My Tickets
Reservations
Waitlists
Favorite Bands
Favorite Venues
Messages
Payments and Refunds
Referrals
Settings
```

## Band account

A Band Account serves bands, solo artists, DJs, ensembles, managers, booking agents, and authorized representatives.

Band accounts can:

- Claim or create an official profile
- Verify representation authority
- Upload biographies, logos, photos, music, approved clips, and press assets
- Connect official YouTube, Facebook, Instagram, TikTok, Spotify, and website properties
- Publish available and blocked dates
- Define desired cities, travel regions, venue capacities, and performance formats
- Upload technical and hospitality riders
- Define indicative price ranges and negotiation constraints
- Receive demand opportunities ranked by real supporter geography and commitment quality
- Accept, decline, counter, or request information
- Sign letters of intent and final agreements electronically
- Review ticket demand, audience geography, and campaign performance
- Receive deposits and settlement through verified payment accounts
- Approve or delegate automated promotional campaigns
- View royalties, ticket allocations, guest lists, merchandise, and settlement reports

A fan-created campaign must remain clearly labeled:

```text
Fan-proposed campaign.
The band has not confirmed participation.
```

After verification, the platform may display an **Official Band** badge and identify the verified representative role.

Suggested navigation:

```text
Artist Profile
Demand Opportunities
Availability
Booking Requests
Offers and Contracts
Riders
Media Library
Confirmed Shows
Ticket Allocations
Marketing
Payments
Audience Analytics
Team and Permissions
```

## Venue account

A Venue Account serves concert halls, theaters, clubs, bars, restaurants, hotels, warehouses, rooftops, farms, outdoor spaces, community spaces, arenas, and temporary event locations.

Venue accounts can:

- Manage one or more spaces
- Publish standing, seated, legal, sellable, accessible, and section-level capacities
- Maintain availability, holds, maintenance, load-in, and load-out calendars
- Define rental models, minimum spends, revenue shares, deposits, overtime, and cancellation rules
- Upload photos, floor plans, seating maps, technical specifications, accessibility information, and loading instructions
- List included audio, lighting, stage, video, power, internet, furniture, and staffing
- Define age, alcohol, curfew, noise, insurance, security, union, and preferred-vendor requirements
- Receive matched event opportunities
- Submit standardized quotes
- Negotiate within approved rules
- Issue first holds, second holds, and contracts
- Receive deposits and final payments
- Coordinate ticket capacity, production schedules, and supplier access
- Review event history, conversion, attendance, and marketplace reputation

Suggested navigation:

```text
Venue Listings
Spaces and Capacities
Availability Calendar
Event Matches
Quote Requests
Holds
Contracts
Included Equipment
Production Schedule
Upcoming Events
Payments
Reviews
Analytics
Team and Permissions
```

## Equipment rental company account

Rental companies can:

- Create a verified business profile
- Define service locations and delivery radius
- Publish serialized and non-serialized inventory
- Create equipment packages
- Maintain availability and maintenance status
- Set daily, weekly, labor, delivery, setup, pickup, deposit, waiver, and replacement pricing
- Receive requirements generated from a band rider and venue inventory gap
- Submit standardized all-in quotes
- Reserve inventory after contract execution
- Assign drivers, technicians, and operators
- Scan delivery and return items
- Record condition photos and damage disputes
- Receive milestone-based payments
- Maintain reliability and fulfillment history

## Event organizer or promoter account

Organizers can:

- Plant and operate demand campaigns
- Manage multiple brands and clients
- Configure thresholds, refund rules, ticketing, marketing, and budgets
- Create or import event ideas
- Match bands, venues, rentals, professionals, and sponsors
- Compare quotes and approve or delegate selection
- Manage contracts, insurance, permits, staffing, and production
- Operate ticket sales, guest lists, access control, and settlement
- Run white-label campaign pages and connected social channels

## Event professional account

Possible professional categories include:

- Event producer
- Production manager
- Booking agent
- Tour manager
- Sound engineer
- Lighting engineer
- Video technician
- Stage manager
- Security provider
- Photographer or videographer
- Designer or social-media manager
- Ticketing and entrance staff
- Driver, loader, electrician, caterer, bartender, medic, cleanup company
- Insurance, permit, legal, and accounting provider

Profiles contain service area, availability, rate structure, certifications, insurance, portfolio, equipment, languages, reviews, and cancellation terms.

## Sponsor account

Sponsors can:

- Define target cities, audiences, event categories, and budgets
- Discover campaigns with verified demand
- Receive matched sponsorship opportunities
- Select packages and activation inventory
- Sign agreements and fund approved campaigns
- Receive attribution, impressions, ticket, engagement, and attendance reports

## Multi-tenant identity and authorization

Identity and business authorization must remain separate.

```text
Identity: the human being who authenticated
Organization: the legal or operating account
Membership: the user’s role inside the organization
Resource authorization: what the membership may do to a specific event or asset
```

Recommended organization roles:

```text
OWNER
ADMIN
FINANCE_MANAGER
BOOKING_MANAGER
MARKETING_MANAGER
PRODUCTION_MANAGER
BOX_OFFICE_MANAGER
CONTENT_EDITOR
VIEWER
```

Sensitive actions require stronger permissions and recent authentication:

- Connecting or changing settlement accounts
- Approving contracts
- Charging saved payment methods
- Releasing or refunding funds
- Changing capacity
- Cancelling an event
- Publishing a confirmation announcement
- Changing account ownership

---

# Future authentication and connected services

## Sign-on providers

Future authentication options:

- Continue with Google
- Continue with Facebook
- Continue with Apple
- Continue with Microsoft
- Continue with LinkedIn
- Continue with TikTok
- Email and password
- Passwordless email link
- Passkeys when supported by the chosen identity provider

## Login is not channel authorization

Authentication must be separate from publishing and business-data connections.

```text
Continue with Google
    → authenticate a platform user

Connect YouTube
    → authorize channel publishing and analytics
```

```text
Continue with Facebook
    → authenticate a platform user

Connect Meta Business
    → select Pages, Instagram professional accounts, ad accounts,
      datasets, lead forms, and Messenger assets
```

## Account linking

- Use the provider’s permanent subject identifier.
- Require verified ownership before linking identities.
- Never merge accounts by display name.
- Do not rely on email as the only permanent external identity key.
- Require reauthentication before linking or unlinking a provider.
- Prevent removal of the final usable login method.
- Notify the account owner when identity connections change.
- Maintain an audit trail for merges, splits, and ownership transfers.

## Connected-service vault

Store third-party tokens only in encrypted server-side storage or a secrets vault.

Suggested connection record:

```json
{
  "organization_id": "org_123",
  "provider": "youtube",
  "external_account_id": "UC...",
  "scopes": ["youtube.upload"],
  "": "vault-reference",
  "status": "connected",
  "last_verified_at": "2026-07-30T10:00:00Z",
  "last_error_code": null
}
```

Connection health should be monitored automatically. Revoked permissions pause only the affected workflow and preserve queued content for reconnection.

---

# Future autonomous brand and channel factory

## Goal

After onboarding, the system can generate a complete campaign or channel identity from structured event information.

```text
Event seed
    ↓
Name and positioning suggestions
    ↓
Visual direction
    ↓
Logo symbol and SVG wordmark
    ↓
Brand kit
    ↓
Channel banners and profile assets
    ↓
Video templates, thumbnail templates, intro, and outro
    ↓
Default copy, links, disclosure rules, and publishing calendar
```

## Generated brand package

```text
logo-primary.svg
logo-primary.png
logo-square.png
logo-dark.png
logo-light.png
profile-image.png
youtube-banner.png
facebook-cover.png
instagram-profile.png
video-watermark.png
thumbnail-template.svg
intro-animation.mp4
outro-animation.mp4
brand-tokens.json
brand-guidelines.pdf
```

## Brand automation rules

- Generate an image symbol separately from the wordmark to avoid malformed AI lettering.
- Construct the wordmark with deterministic SVG typography.
- Use approved, redistributable fonts.
- Verify exact brand-name spelling.
- Verify contrast and small-size readability.
- Generate light, dark, transparent, square, and horizontal variants.
- Prevent unauthorized use of an artist’s official marks.
- Clearly distinguish platform brand, organizer brand, campaign brand, and artist brand.
- Route probable trademark conflicts to review.
- Keep the original generation prompt, model version, asset lineage, and approval history.

## Channel bootstrap

After a customer connects an existing authorized channel, the platform can prepare:

- Channel description
- Banner
- Watermark
- Default links
- Default descriptions
- Playlists
- Channel trailer
- First campaign content set
- Upload schedule
- Comment and escalation rules
- Analytics baseline

Some third-party platforms do not expose every profile action through a supported API. In those cases, the platform should generate the asset and provide a guided one-step customer action rather than using unsupported browser automation.

---

# Future autonomous marketing module

## Marketing operating model

The marketing system reacts to event state, inventory, demand, geography, and performance rather than publishing from a static calendar alone.

```text
Verified event state changes
        ↓
Rules engine selects objective
        ↓
Content engine creates platform-specific variants
        ↓
Policy and factual validation
        ↓
Organic publishing and approved paid campaigns
        ↓
Attribution and conversion collection
        ↓
Budget and creative optimization
        ↓
Next action generated from real event results
```

## Supported future channels

- Facebook Pages
- Facebook Reels
- Facebook Event sharing workflow
- Facebook Groups through compliant tracked sharing rather than arbitrary automated posting
- Instagram professional accounts and Reels
- Messenger
- Meta Lead Ads
- Meta Ads
- YouTube Shorts and long-form video
- TikTok posting or draft workflows where approved
- Google Ads
- Email
- SMS
- WhatsApp Business where approved
- Push notifications
- Partner, influencer, ambassador, and community links
- Organizer and venue websites through widgets or APIs

## Marketing campaign stages

### Seed validation

Purpose: determine whether a real local audience exists.

Automations:

- Generate campaign identity and seed landing page
- Publish question-based Shorts and Reels
- Generate tracked community-sharing packages
- Run low-budget demand tests within customer limits
- Collect city, ZIP code, quantity, price range, and preferred dates
- Retarget consenting visitors and video viewers
- Calculate cost per verified supporter
- Stop or revise weak campaigns before major commitments

### Funding and reservation stage

Purpose: reach supporter, commitment, or protected-funding thresholds.

Automations:

- Display real progress
- Publish milestone content
- Generate supporter referral links
- Send opted-in reminders
- Increase focus in high-conversion geography
- Invite suitable sponsors
- Suppress language that implies a confirmed booking

### Artist and venue confirmation stage

Purpose: maintain momentum while negotiations occur.

Automations:

- Publish accurate “confirmation in progress” updates
- Present proposed venue types without false confirmation
- Collect waitlist and reservation interest
- Invite matching venues and sponsors
- Reduce ticket-sale claims until contracts permit conversion

### Confirmed-event stage

Purpose: convert supporters into paid attendees.

Automations:

- Replace proposal copy with confirmed-event copy
- Publish signed artist and venue status
- Launch early-supporter and public ticket windows
- Charge previously authorized commitments only under accepted terms
- Generate press, partner, community, and sponsor packages
- Start ticket-conversion advertising

### Ticket optimization stage

```text
Under 25% sold
→ test new hooks, landing pages, audiences, and ticket offers

25–50% sold
→ scale proven creatives gradually

50–75% sold
→ emphasize verified social proof

75–90% sold
→ increase urgency within frequency limits

90–99% sold
→ use truthful limited-inventory messages

Sold out
→ stop sales campaigns and open waitlist
```

### Event-day stage

- Send verified entry, time, transit, accessibility, and prohibited-item information
- Publish day-of-show content
- Advertise door inventory only when available
- Stop sales automatically at capacity
- Collect attendee media through approved submission links

### Post-event stage

- Generate highlights
- Publish thank-you content
- Request verified reviews
- Generate sponsor and organizer reports
- Invite attendees to relevant future seeds
- Create audiences from properly consented first-party data
- Archive expired calls to action

## Content factory

For each event, the system can generate a configurable set of:

- Seed videos
- Artist-story videos
- City-demand videos
- Supporter milestone videos
- Funding milestone videos
- Venue reveal videos
- Sponsor content
- Ticket-launch content
- Ticket-progress content
- Countdown content
- Event-day content
- Cancellation or postponement notices
- Post-event highlights
- Email sequences
- SMS messages
- Messenger responses
- Community-group copy
- Press-release drafts
- Ad creative variants

Each platform receives a separate caption, hook, format, duration, safe area, CTA, and tracking link.

## Automated video pipeline

```text
Campaign trigger
    ↓
Generate hooks and script
    ↓
Validate facts against canonical event data
    ↓
Select approved media
    ↓
Generate narration where enabled
    ↓
Generate timed captions
    ↓
Render platform-specific formats
    ↓
Run technical, factual, rights, and duplication checks
    ↓
Generate title, description, thumbnail, and disclosure data
    ↓
Schedule or publish
    ↓
Record external IDs and collect analytics
```

Recommended rendering components:

- FFmpeg for deterministic composition and encoding
- A job queue for horizontal scaling
- Object storage for source and rendered media
- Speech generation with an approved local or hosted model
- Caption generation with an approved speech-to-text model
- Template versioning for reproducibility

## Content rules

- State artist, venue, date, capacity, price, and deadline only from verified fields.
- Never use “confirmed” before the required contract gates.
- Never generate false scarcity or fake countdowns.
- Use only approved or licensed music, images, video, and trademarks.
- Apply synthetic-media disclosures when required.
- Keep captions inside safe areas.
- Avoid mass-producing nearly identical content.
- Stop or update scheduled content after cancellation, postponement, venue changes, or sellout.
- Preserve the generated, approved, scheduled, and published versions.

## Creative testing

- Generate materially different hooks, visual sequences, and calls to action.
- Start with bounded test budgets.
- Optimize for verified supporters, reservations, or ticket purchases rather than clicks alone.
- Require a minimum evidence threshold before declaring a winner.
- Move budget gradually.
- Enforce daily, lifetime, per-channel, and per-event caps.
- Maintain minimum refund and production reserves.
- Pause ads immediately when the event is cancelled, expired, or sold out.

## Marketing budget controller

Example customer constraints:

```json
{
  "maximum_campaign_budget": 5000,
  "maximum_daily_spend": 250,
  "maximum_cost_per_supporter": 8,
  "maximum_cost_per_ticket": 15,
  "minimum_protected_reserve": 20000,
  "automatic_budget_changes": true,
  "maximum_daily_increase_percent": 20
}
```

AI may recommend a change, but the deterministic rules engine enforces the limits.

## Attribution model

Track the complete funnel:

```text
Impression
→ View
→ Campaign visit
→ Supporter
→ Reservation
→ Payment commitment
→ Ticket purchase
→ Ticket scan
→ Attendance
→ Repeat supporter
```

Recommended attribution fields:

```text
organization_id
event_id
campaign_id
channel
source
source_label
referral_code
creative_id
audience_id
placement
landing_page_version
click_id
browser_event_id
server_event_id
order_id
ticket_id
```

---

# Future Meta/Facebook Business integration

## Meta app responsibilities

A future Meta Business App may support, subject to permissions and review:

- Facebook Login
- Page discovery and authorization
- Page post publishing
- Facebook Page Reel publishing where available
- Instagram professional publishing
- Meta Ads management
- Lead Ads ingestion
- Messenger conversations
- Meta Pixel
- Conversions API
- Webhooks and connection-health monitoring
- Campaign and advertising insights

## Facebook Event strategy

The native platform event remains authoritative.

Where unrestricted Facebook Event creation or modification is not available to the application, generate a complete event package:

- Event title
- Description
- Cover image
- Date and time
- Address
- Ticket or campaign URL
- Host instructions

Then provide a guided creation step and store the resulting Facebook Event URL.

## Facebook Group strategy

Do not automate arbitrary personal activity or unsupported Group posting.

Use:

- Group-specific tracked links
- Community-specific copy
- Admin or ambassador approvals
- Share Dialog and supported interfaces
- Group rules and permission records
- Conversion and attendance attribution

## Messenger assistant

The assistant can answer from canonical event data:

- Confirmation status
- Date and time
- Venue and directions
- Ticket price and availability
- Refund terms
- Age restrictions
- Accessibility information
- Supporter and funding progress
- Sponsor or vendor inquiry routing

Disputes, threats, emergencies, legal questions, sensitive accessibility issues, and unsupported refund requests enter an escalation queue.

## Lead Ads

Lead forms can support:

- Demand registration
- Ticket alerts
- Sponsor inquiries
- Venue applications
- Vendor applications
- Artist submissions
- Volunteer registrations
- VIP waitlists

Every lead must carry consent source, form version, campaign, event, timestamp, and permitted communication channels.

---

# Future YouTube channel automation

After one-time OAuth authorization, the platform can automate:

- Shorts generation
- Video uploads
- Titles, descriptions, tags, and privacy status
- Custom thumbnails
- Scheduling
- Playlist assignment
- Comment monitoring and escalation where permitted
- Analytics ingestion
- Campaign-link attribution
- Milestone-driven content generation

Suggested content sequence:

```text
1. Should this band play this city?
2. Why this event matters
3. Supporter target explanation
4. 25% progress
5. 50% progress
6. 75% progress
7. Almost there
8. Artist and venue confirmation
9. Ticket launch
10. Seven-day countdown
11. Final inventory
12. Event-day information
13. Thank-you and highlights
```

Uploads should use resumable upload, idempotent jobs, retry with exponential backoff, and reconciliation against the stored YouTube video ID.

---

# Future ticketing module

## Ticket products

- Free supporter registration
- Refundable campaign reservation
- Early-supporter ticket
- Early-bird ticket
- General admission
- Reserved seating
- VIP
- Group package
- Sponsor allocation
- Artist guest list
- Venue hold
- Accessibility allocation
- Promotion code
- Door ticket
- Waitlist offer

## Ticket lifecycle

```text
AVAILABLE
  ↓
HELD
  ↓
PAYMENT_PENDING
  ↓
SOLD
  ↓
ISSUED
  ↓
SCANNED
  ↓
ATTENDED
```

Alternative states:

```text
WAITLISTED
TRANSFERRED
REFUNDED
VOIDED
DISPUTED
NO_SHOW
EXPIRED
```

## Campaign-to-ticket conversion

```text
Demand campaign
    ↓
Supporter or refundable reservation
    ↓
Threshold reached
    ↓
Artist and venue contracts completed
    ↓
Capacity and final terms verified
    ↓
Eligible reservations converted under accepted rules
    ↓
Public ticket inventory opened
```

## Inventory rules

- Temporarily lock selected inventory during checkout.
- Release expired holds automatically.
- Never sell beyond verified sellable capacity.
- Separate sponsor, venue, artist, accessibility, production, and general-public holds.
- Prevent duplicate reserved-seat sales.
- Stop sales automatically at capacity.
- Require authorized capacity changes.
- Reconcile venue capacity changes against sold inventory before accepting them.

## Pricing rules

- Display mandatory charges before final confirmation.
- Never change the price of a ticket already purchased.
- Do not create artificial scarcity.
- Use dynamic pricing only with explicit organizer authorization and jurisdictional review.
- Preserve every price, fee, tax, discount, and rule revision.

## QR tickets and access control

Each ticket should contain a signed opaque token rather than personal or payment information.

The scanner application should:

- Support intermittent connectivity
- Detect duplicate scans
- Display ticket type and seat
- Enforce allowed entry count
- Record manual overrides
- Synchronize offline scans safely
- Show current occupancy
- Escalate invalid, refunded, transferred, or disputed tickets

## Transfers and waitlist

A transfer invalidates the prior QR token and generates a new token after recipient acceptance.

A waitlist offer holds released inventory for a limited time before offering it to the next eligible person.

## Refund rules

Automatic refund workflows may be triggered by:

- Threshold failure
- Artist confirmation failure
- Venue confirmation failure
- Event cancellation
- A qualifying material date or location change
- Organizer-authorized refund
- Published campaign guarantee
- Applicable law or payment dispute outcome

All refunds update the payment provider and the internal double-entry ledger.

---

# Future venue marketplace

## Venue listing data

```text
Venue identity and operator
Address and coordinates
Space type
Standing, seated, legal, sellable, and accessible capacity
Availability and holds
Rate plans
Deposit and cancellation rules
Age and alcohol rules
Curfew and noise rules
Insurance and security requirements
Stage, loading, power, rigging, audio, lighting, video, and internet
Dressing rooms, green room, restrooms, parking, transit, and accessibility
Included equipment and staff
Preferred and required vendors
Photos, floor plans, seating charts, technical documents, and reviews
```

## Availability states

```text
AVAILABLE
INQUIRY
SOFT_HOLD
FIRST_HOLD
SECOND_HOLD
QUOTE_SENT
CONTRACT_PENDING
CONFIRMED
BLOCKED
MAINTENANCE
```

## Venue pricing models

- Flat event rental
- Hourly rental
- Minimum food or beverage spend
- Ticket-revenue percentage
- Flat fee plus revenue percentage
- Per-attendee rate
- Rehearsal package
- Production package
- Multi-day package

The comparison engine must calculate the complete price, including required staff, security, cleaning, utilities, equipment, taxes, overtime, insurance, and other mandatory charges.

## Venue matching score

Example weighting:

```text
Capacity fit                 20%
Confirmed availability      20%
Budget fit                   15%
Supporter proximity         15%
Technical fit               10%
Transportation               5%
Accessibility                5%
Cancellation flexibility     5%
Historical event success     5%
```

Hard constraints are evaluated before scoring. A venue that fails legal capacity, date, safety, accessibility, or critical technical constraints is not selectable even if its score is high.

## Venue booking workflow

```text
Campaign reaches negotiation stage
    ↓
Generate venue requirements
    ↓
Select top compliant venues
    ↓
Send standardized quote requests
    ↓
Normalize offers
    ↓
Rank price, terms, and operational fit
    ↓
Place supported temporary hold
    ↓
Generate agreement
    ↓
Collect authorized signatures
    ↓
Schedule approved deposit
    ↓
Mark venue confirmed
```

---

# Future equipment rental marketplace

## Equipment categories

- Audio
- Lighting
- Stage and rigging
- Video and streaming
- Power and generators
- Networking and temporary internet
- Barricades and entrance equipment
- Furniture and tents
- Heating and cooling
- Radios and communications
- Ticket scanners and box-office equipment
- Catering and refrigeration
- Transportation and logistics
- Sanitation and temporary restrooms

## Requirement generation

The system calculates the rental shortage from:

```text
Band technical rider
+ Venue technical inventory
+ Event format
+ Attendance
+ Stage size
+ Indoor or outdoor conditions
+ Streaming requirements
+ Safety and backup requirements
- Band-provided equipment
- Venue-included equipment
- Organizer-owned equipment
= Rental requirements
```

## Inventory record

```text
Category
Manufacturer and model
Technical specifications
Quantity owned
Quantity available
Serial number where applicable
Condition
Maintenance status
Daily and weekly pricing
Deposit and replacement value
Operator requirement
Power and compatibility data
Delivery and setup requirements
Availability calendar
```

## Inventory states

```text
AVAILABLE
HELD
RESERVED
PREPARING
IN_TRANSIT
DELIVERED
CHECKED_IN
IN_USE
CHECKED_OUT
RETURNED
INSPECTION
MAINTENANCE
DAMAGED
LOST
```

## Vendor matching score

```text
Technical compliance        30%
Availability                20%
Complete delivered price    20%
Reliability                 10%
Distance                     5%
Insurance                    5%
Replacement capability       5%
Cancellation flexibility     5%
```

## Rental workflow

```text
Production requirements approved
    ↓
Calculate equipment gap
    ↓
Create rental packages
    ↓
Invite qualified local vendors
    ↓
Receive standardized quotes
    ↓
Verify specifications and full cost
    ↓
Select compliant primary and backup suppliers
    ↓
Sign rental agreement
    ↓
Reserve inventory
    ↓
Schedule delivery, setup, operation, pickup, and return
    ↓
Verify serial numbers and condition
    ↓
Release milestone payments
```

## Critical rental rules

- Never substitute a critical item with a lower specification without authorization.
- Verify voltage, phase, load, connectors, rigging limits, and venue compatibility.
- Prevent double booking of serialized inventory.
- Include labor, delivery, setup, breakdown, pickup, tax, insurance, and damage waivers in comparisons.
- Maintain backup suppliers for critical single points of failure.
- Record delivery and return condition with photos.
- Freeze disputed damage amounts while the remaining undisputed balance proceeds.

---

# Future event-team matching marketplace

## Marketplace sides

```text
Demand side
├── Users and supporters
├── Organizers and promoters
├── Bands seeking verified audiences
└── Sponsors seeking relevant events

Supply side
├── Bands and representatives
├── Venues
├── Rental companies
├── Event professionals
├── Production companies
└── Marketing and community partners
```

## Match inputs

- Event city and travel radius
- Date range
- Attendance and capacity
- Budget
- Event category and audience
- Technical requirements
- Accessibility
- Age and alcohol rules
- Insurance and certification requirements
- Availability
- Historical fulfillment
- Response time
- Cancellation rate
- Reviews and disputes

## Match workflow

```text
Event requirement generated
    ↓
Hard-constraint filtering
    ↓
Marketplace scoring
    ↓
Top suppliers invited
    ↓
Standardized quotes received
    ↓
Compliance and cost validation
    ↓
Best primary and backup options recommended
    ↓
Automatic selection inside customer limits or approval request
    ↓
Contract and payment milestones created
```

## Competitive bidding

- Suppliers cannot view confidential competitor pricing.
- The lowest price does not automatically win.
- Quotes must include mandatory charges.
- Material exclusions are explicit.
- All revisions are preserved.
- Technical and safety noncompliance disqualifies an offer.
- Featured placement must not override compliance or match quality.

## Shared event workspace

Every accepted match receives:

```text
Requirements
Messages
Quote and revisions
Contract
Files
Calendar
Tasks
Payment milestones
Delivery or service status
Disputes
Reviews
```

## Reputation

Verified marketplace reputation may include:

- Completed bookings
- Average review
- Response time
- Quote accuracy
- Cancellation rate
- On-time delivery or arrival
- Technical compliance
- Dispute and refund rate
- Identity, insurance, and certification status

Only completed or otherwise verified transactions can create verified reviews.

---

# Future demand, funding, and money model

## Levels of commitment

### Free support

A user confirms interest and provides useful demand data without payment.

### Authorized future payment

A user saves a payment method and provides explicit permission for a later conditional charge under stated terms. Long campaign periods should not depend on a card authorization hold that may expire.

### Paid refundable reservation

A user pays a refundable amount under published campaign terms and the actual payment-protection arrangement.

## Escrow terminology

Stripe Connect can control the timing and routing of marketplace funds, but Stripe does not itself provide legal escrow accounts. The platform must not use the word **escrow** unless a qualified regulated partner and legal structure support that claim.

Until then, use accurate language such as:

```text
Protected event funds
Refundable event reservation
Funds held under the published campaign terms
```

## Funding models

### Strict supporter-protection model

```text
Supporter funds remain protected until verified show completion.
The organizer finances pre-show deposits through sponsors, credit, or working capital.
```

### Controlled milestone-release model

```text
A disclosed portion remains protected.
Limited releases fund verified artist, venue, insurance, or production obligations.
The remaining amount is released after verified performance and reconciliation.
```

The selected model and every release condition must be visible before payment.

## Double-entry event ledger

Each campaign and event requires an internal ledger for:

```text
Supporter funds
Ticket revenue
Sponsor funds
Taxes
Processor fees
Platform fees
Refund reserve
Artist allocation
Venue allocation
Rental allocation
Professional allocation
Marketing spend
Released funds
Protected funds
Refunds
Chargebacks
Final organizer balance
```

External processor balances are reconciled against the internal ledger; they do not replace it.

## Release evidence

Possible evidence gates:

```text
Artist agreement signed
Venue agreement signed
Insurance verified
Permit verified
Equipment delivered
Staff checked in
Show started
Minimum performance completed
Venue confirmation received
No active cancellation or payment freeze
Settlement approved
```

Every release is idempotent, policy-checked, and auditable.

## Event target calculation

```text
Total required cost =
artist
+ venue
+ production
+ labor
+ security
+ insurance
+ permits
+ travel and hospitality
+ marketing
+ payment costs
+ taxes
+ platform fees
+ contingency
```

```text
Required paid attendance =
Total required cost ÷ Net revenue per paid attendee
```

Target rules:

- Include configurable contingency.
- Do not count free supporters as paid attendees.
- Weight verified local paid commitments more strongly than anonymous interest.
- Recalculate after accepted quotes.
- Preserve prior customer terms when costs change.
- Require acceptance or refund for material changes.

---

# Future contracts and negotiation automation

## Negotiation boundaries

AI-assisted negotiation may operate only inside explicit authority:

```json
{
  "maximum_artist_guarantee": 25000,
  "maximum_artist_deposit_percent": 10,
  "permitted_dates": ["2026-10-01", "2026-10-15"],
  "minimum_performance_minutes": 75,
  "required_cancellation_protection": true,
  "required_insurance_language": true
}
```

Anything outside these boundaries becomes an exception.

## Contract workflow

```text
Accepted standardized quote
    ↓
Choose approved template
    ↓
Insert event, supplier, price, milestones, and cancellation terms
    ↓
Run consistency checks
    ↓
Send to authorized signers
    ↓
Verify e-signature completion
    ↓
Store immutable signed copy and hash
    ↓
Activate booking and payment schedule
```

No artist, venue, or supplier is marked `CONFIRMED` until required signatures and conditions are satisfied.

---

# Future production operations

After confirmation, generate:

- Master production calendar
- Critical path
- Artist and venue obligations
- Technical rider checklist
- Hospitality checklist
- Vendor assignments
- Security and medical plan
- Insurance checklist
- Permit checklist
- Staffing schedule
- Load-in, soundcheck, doors, performance, curfew, and load-out runbook
- Ticketing and entrance plan
- Sponsor activation plan
- Accessibility plan
- Communication tree
- Emergency contacts
- Settlement worksheet

## Production rules

- No `SHOW_READY` state without required insurance, capacity, safety, and critical supplier checks.
- No overselling beyond verified capacity.
- No unauthorized band substitution.
- No major date or venue change without required notice and acceptance.
- Critical equipment and staff require primary and backup plans.
- All operational changes propagate to tickets, marketing, messages, suppliers, and calendars.

## Show verification

Final settlement should not depend on one organizer click.

Possible verification signals:

- Ticket scans
- Venue-authorized confirmation
- Production-manager confirmation
- Scheduled and actual timestamps
- Approved staff-device check-in
- Photographic or video evidence
- Minimum performance duration
- Absence of cancellation, safety, or payment freeze

Conflicting evidence freezes affected settlement and creates an exception case.

---

# Future lifecycle state machines

## Demand campaign

```text
DRAFT
  ↓
COLLECTING
  ↓
TARGET_REACHED
  ↓
CONFIRMING
  ↓
CONFIRMED
  ↓
CONVERTING
  ↓
LIVE
  ↓
COMPLETED
  ↓
SETTLED
```

Failure paths:

```text
COLLECTING + deadline missed → REFUNDING → REFUNDED
CONFIRMING + artist unavailable → ALTERNATIVE_OFFER or REFUNDING
CONFIRMING + venue unavailable → ALTERNATIVE_OFFER or REFUNDING
Any pre-show cancellation → CANCELLING → REFUNDING
Dispute or verification conflict → FROZEN
```

## Supplier booking

```text
MATCHED
→ INVITED
→ QUOTE_PENDING
→ QUOTED
→ SELECTED
→ CONTRACT_PENDING
→ CONFIRMED
→ IN_PREPARATION
→ DELIVERING
→ DELIVERED
→ COMPLETED
→ SETTLED
```

## Marketing job

```text
PLANNED
→ GENERATING
→ VALIDATING
→ APPROVAL_PENDING optional
→ SCHEDULED
→ PUBLISHING
→ PUBLISHED
→ MEASURING
→ OPTIMIZING
```

## Video job

```text
QUEUED
→ SCRIPTING
→ ASSET_SELECTION
→ AUDIO_GENERATION
→ CAPTIONING
→ RENDERING
→ QUALITY_CHECK
→ READY
→ SCHEDULED
→ UPLOADING
→ PUBLISHED
```

Failure states use bounded retries, dead-letter queues, and `NEEDS_ATTENTION` rather than silently abandoning work.

---

# Future architecture

## Architecture goals

- Multi-tenant isolation
- Durable long-running workflows
- Strong financial consistency
- Idempotent integrations
- Independent video-render scaling
- Real-time event updates
- Auditable state transitions
- Graceful degradation when social APIs fail
- Clear boundaries between implemented MVP and future services
- Ability to begin as a modular monolith and extract services as volume grows

## Recommended evolution path

Start with a **modular monolith** using strict bounded contexts and an outbox. Extract high-load or high-risk workloads only when operational evidence justifies it.

```text
Phase 1
Django modular monolith + PostgreSQL + Redis + workers

Phase 2
Dedicated media workers, durable workflow engine, search, analytics warehouse

Phase 3
Selective service extraction for payments, ticketing, media, and marketplace
```

## High-level system context

```text
Users / Bands / Venues / Organizers / Suppliers / Sponsors
                         │
                         ▼
               Web App and Mobile PWA
                         │
                         ▼
              API Gateway / Backend API
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Core Event OS     Marketplace OS    Marketing OS
        │                │                │
        ├──────────────┬─┴──────────────┐ │
        ▼              ▼                ▼ ▼
 Payments/Ledger   Ticketing        Media Factory
        │              │                │
        └──────────────┴───────┬────────┘
                               ▼
                     Workflow and Event Bus
                               │
        ┌───────────────┬──────┴───────────────┐
        ▼               ▼                      ▼
 Social Platforms   Payment Partners     Email/SMS/E-sign
```

## Logical components

### Web application

- Public discovery and campaign pages
- User dashboard
- Band dashboard
- Venue dashboard
- Supplier dashboard
- Organizer operations console
- Sponsor portal
- Admin and exception console
- Scanner PWA

### API gateway or backend-for-frontend

Responsibilities:

- Authentication and session validation
- Tenant and role resolution
- Request rate limiting
- Input validation
- Idempotency handling
- API versioning
- Correlation IDs
- Response composition

### Identity and organization module

- Users
- External identities
- Organizations
- Memberships
- Roles and permissions
- Verification status
- Connected-service authorization

### Campaign module

- Seeds
- Thresholds
- Supporters
- Reservations
- Sponsor commitments
- Campaign state machine
- Conversion to confirmed event

### Event module

- Canonical event record
- Dates and locations
- Band and venue confirmations
- Capacity
- Production status
- Event lifecycle

### Marketplace module

- Listings
- Requirements
- Matching
- Invitations
- Quotes and revisions
- Selection
- Reviews and reputation

### Venue module

- Spaces
- Capacities
- Rate plans
- Availability and holds
- Technical inventory
- Venue contracts

### Rental module

- Catalog
- Serialized inventory
- Packages
- Availability
- Quotes
- Deliveries
- Returns
- Damage claims

### Ticketing module

- Ticket types
- Inventory
- Holds
- Orders
- Payments
- Tickets
- Transfers
- Waitlists
- QR tokens
- Scans
- Refunds

### Contract module

- Templates
- Negotiation constraints
- Generated documents
- Signers
- Signature status
- Evidence and immutable signed copies

### Payment and ledger module

- Payment intents and saved-method authorizations
- Connected accounts
- Charges
- Transfers
- Refunds
- Disputes
- Payout milestones
- Double-entry ledger
- Reconciliation

### Marketing module

- Strategies
- Rules
- Calendars
- Content plans
- Organic posts
- Ads
- Leads
- Attribution
- Analytics
- Budget control

### Media factory

- Brand generation
- Asset ingestion
- Script generation
- Voice and captions
- Video rendering
- Thumbnail generation
- Quality checks
- Publishing payloads

### Production module

- Tasks
- Runbooks
- Staff
- Suppliers
- Insurance and permits
- Show-day verification
- Incident and exception management

### Notification module

- Email
- SMS
- Push
- Messenger or WhatsApp where permitted
- Templates
- Preferences
- Suppression and unsubscribe

### Analytics module

- Funnel events
- Marketing performance
- Demand geography
- Ticket sales
- Attendance
- Supplier performance
- Sponsor reports
- Financial reporting

## Data architecture

### PostgreSQL

System of record for transactional and financial state.

Recommended techniques:

- Row-level tenant isolation where appropriate
- Strong foreign keys and check constraints
- Serializable or carefully designed transactional operations for inventory and threshold transitions
- Optimistic concurrency for ordinary edits
- Append-only audit events
- Transactional outbox

### Redis

- Short-lived cache
- Rate limits
- Distributed locks only where unavoidable
- Job queues
- WebSocket fan-out
- Ticket inventory hold expiration

Redis must not be the only source of truth for money, orders, tickets, capacity, or contractual state.

### Object storage

Store:

- Uploaded source media
- Generated brand assets
- Rendered videos
- Signed contracts
- Technical riders
- Floor plans
- Insurance certificates
- Delivery and condition photos
- Reports

Use private buckets, short-lived signed URLs, malware scanning, file-type validation, and content hashes.

### Search index

A search engine may support:

- Venue search
- Equipment search
- Professional search
- Band and event discovery
- Geographic filtering
- Marketplace facets

The transactional database remains authoritative.

### Analytics warehouse

High-volume click, view, ad, conversion, scan, and operational telemetry should flow into a warehouse or lakehouse rather than burdening transactional queries.

## Durable workflow engine

Long-running workflows can span days or months and include retries, deadlines, external callbacks, and compensation.

Recommended candidates:

- Temporal for critical durable workflows
- Celery or equivalent workers for shorter background jobs
- n8n for low-risk integrations, notifications, and administrative automations

Do not use a low-code workflow alone as the system of record for contracts, inventory, ticket ownership, refunds, or ledger balances.

Example durable workflow:

```text
Campaign launched
→ wait for supporter or amount threshold
→ start artist and venue match workflows
→ wait for signed agreements or deadline
→ compensate with alternatives or refunds on failure
→ convert reservations
→ open ticket sales
→ monitor production gates
→ verify event completion
→ reconcile and settle
```

## Event bus and transactional outbox

Domain services publish events only after their database transaction succeeds.

Suggested events:

```text
identity.user_created
organization.created
organization.member_added
social.connection_authorized
social.connection_revoked

campaign.created
campaign.launched
campaign.supporter_added
campaign.reservation_created
campaign.sponsor_committed
campaign.target_reached
campaign.confirmation_started
campaign.failed
campaign.refund_started
campaign.refunded
campaign.finalized

artist.invited
artist.offer_sent
artist.confirmed
artist.declined

venue.match_created
venue.quote_requested
venue.quote_received
venue.hold_created
venue.confirmed
venue.cancelled

rental.requirement_created
rental.quote_requested
rental.quote_received
rental.booking_confirmed
rental.delivered
rental.returned
rental.damage_reported

contract.generated
contract.sent
contract.signed
contract.expired

payment.authorized
payment.captured
payment.failed
payment.refunded
payment.disputed
ledger.entry_posted
payout.release_approved
payout.released

inventory.ticket_held
inventory.ticket_released
order.created
order.paid
ticket.issued
ticket.transferred
ticket.scanned
ticket.refunded

marketing.plan_created
marketing.content_generated
marketing.content_published
marketing.lead_received
marketing.budget_adjusted

media.render_started
media.render_completed
media.quality_failed
social.post_published
social.post_failed

event.show_ready
event.started
event.completed
event.settlement_started
event.settled
```

Consumers must be idempotent. Event schemas are versioned.

## Rules engine

The rules engine evaluates deterministic policies such as:

- Threshold reached
- Campaign deadline missed
- Artist and venue confirmation gates
- Ticket capacity
- Marketing budget limits
- Refund eligibility
- Supplier compliance
- Payout release evidence
- Venue or equipment conflicts
- Event readiness

Rule decisions should record:

```text
rule_id
rule_version
input_snapshot
result
reason
actor or automation identity
correlation_id
timestamp
```

## AI orchestration boundary

AI services may:

- Generate names, scripts, graphics, summaries, outreach drafts, and recommendations
- Classify messages and leads
- Rank creative variants
- Suggest matches
- Extract structured fields from riders, quotes, and contracts
- Detect anomalies for review

AI services must not independently:

- Change ledger balances
- Release money
- Change legal capacity
- Mark unsigned contracts as confirmed
- Override refund policy
- Invent event facts
- Use unauthorized intellectual property
- Exceed marketing budgets

## Media worker architecture

```text
API creates render job
    ↓
Job queue
    ↓
Worker downloads approved assets
    ↓
Template renderer and FFmpeg
    ↓
Automated quality checks
    ↓
Object storage
    ↓
Publishing job
    ↓
External platform
```

Workers are stateless, horizontally scalable, and use isolated temporary directories. Source files and final outputs are content-addressed or versioned.

## Real-time updates

Use WebSockets or server-sent events for:

- Supporter progress
- Ticket inventory
- Quote status
- Render progress
- Scanner occupancy
- Event readiness
- Incident alerts

Clients should recover from lost connections by refetching authoritative state.

## Suggested deployment topology

```text
CDN and WAF
    ↓
Web frontend
    ↓
Load balancer
    ↓
Django API instances
    ├── PostgreSQL primary and backups
    ├── Redis
    ├── Object storage
    ├── Worker pools
    ├── Durable workflow service
    ├── Search
    └── Observability stack
```

Separate worker pools:

```text
transactional workers
social publishing workers
email and notification workers
media CPU workers
media GPU workers optional
analytics ingestion workers
reconciliation workers
```

## Availability and degradation

- A Meta outage must not block pledges, payments, tickets, refunds, or check-in.
- A YouTube outage queues publishing without losing media.
- A rendering failure retries with a bounded policy and preserves inputs.
- A payment webhook outage is reconciled later by polling and ledger comparison.
- A scanner connectivity outage uses signed offline tickets and later synchronization.
- Search failure falls back to database queries for critical operations.
- Analytics failure never blocks transactional operations.

---

# Future API surface

Illustrative endpoints:

```text
POST   /api/v1/auth/link-provider/
POST   /api/v1/organizations/
POST   /api/v1/organizations/{id}/members/
POST   /api/v1/connections/{provider}/authorize/
DELETE /api/v1/connections/{provider}/{id}/

POST   /api/v1/campaigns/
POST   /api/v1/campaigns/{id}/launch/
POST   /api/v1/campaigns/{id}/support/
POST   /api/v1/campaigns/{id}/reservations/
POST   /api/v1/campaigns/{id}/finalize/
POST   /api/v1/campaigns/{id}/cancel/

GET    /api/v1/bands/{id}/opportunities/
POST   /api/v1/bands/{id}/availability/
POST   /api/v1/artist-offers/{id}/respond/

POST   /api/v1/venues/
POST   /api/v1/venues/{id}/spaces/
POST   /api/v1/venues/{id}/availability/
POST   /api/v1/venue-quotes/{id}/submit/

POST   /api/v1/rental-inventory/
POST   /api/v1/rental-packages/
POST   /api/v1/rental-quotes/{id}/submit/
POST   /api/v1/rental-orders/{id}/delivery/
POST   /api/v1/rental-orders/{id}/return/

POST   /api/v1/events/{id}/requirements/
GET    /api/v1/events/{id}/matches/
POST   /api/v1/events/{id}/quote-requests/
POST   /api/v1/events/{id}/select-offer/

POST   /api/v1/events/{id}/ticket-types/
POST   /api/v1/events/{id}/orders/
POST   /api/v1/tickets/{id}/transfer/
POST   /api/v1/tickets/scan/
POST   /api/v1/orders/{id}/refund/

POST   /api/v1/events/{id}/marketing/plan/
POST   /api/v1/events/{id}/marketing/autopilot/
POST   /api/v1/media/render-jobs/
POST   /api/v1/publishing/jobs/

GET    /api/v1/events/{id}/ledger/
POST   /api/v1/payouts/{id}/approve/
POST   /api/v1/events/{id}/settle/
```

Every mutation should accept an idempotency key where duplicate execution would be harmful.

---

# Future data model

Representative tables or aggregates:

## Identity and tenancy

```text
users
external_identities
organizations
organization_memberships
roles
permissions
verification_cases
connected_accounts
connected_account_tokens
```

## Campaigns and events

```text
campaigns
campaign_thresholds
campaign_supporters
campaign_reservations
campaign_milestones
campaign_sources
events
event_participants
event_status_history
event_requirements
event_incidents
```

## Bands

```text
artist_profiles
artist_representatives
artist_availability
artist_riders
artist_assets
artist_offers
artist_contracts
```

## Venues

```text
venues
venue_spaces
venue_capacities
venue_rate_plans
venue_availability
venue_holds
venue_facilities
venue_technical_specs
venue_assets
venue_quotes
venue_contracts
```

## Rentals and professionals

```text
rental_companies
rental_inventory_items
rental_inventory_units
rental_packages
rental_availability
equipment_requirements
rental_quotes
rental_orders
rental_deliveries
rental_returns
damage_claims
professional_profiles
professional_services
professional_availability
professional_quotes
```

## Marketplace

```text
marketplace_requirements
marketplace_matches
quote_requests
quotes
quote_items
quote_revisions
selected_offers
supplier_bookings
supplier_reviews
supplier_performance_scores
marketplace_disputes
```

## Ticketing

```text
ticket_types
ticket_inventory
ticket_holds
orders
order_items
payments
tickets
ticket_transfers
ticket_waitlists
ticket_scans
promotion_codes
refunds
```

## Contracts and evidence

```text
contract_templates
contracts
contract_parties
contract_signers
contract_versions
contract_evidence
insurance_documents
permit_documents
```

## Finance

```text
payment_customers
payment_methods
connected_payout_accounts
payment_intents
charges
transfers
payout_milestones
refunds
payment_disputes
ledger_accounts
ledger_transactions
ledger_entries
reconciliation_runs
```

## Marketing and media

```text
brand_kits
media_assets
media_rights
content_templates
marketing_plans
marketing_rules
content_items
content_variants
render_jobs
quality_checks
publishing_jobs
published_posts
ad_campaigns
ad_sets
ad_creatives
marketing_budgets
leads
attribution_events
analytics_snapshots
```

## Operations

```text
production_tasks
production_schedules
staff_assignments
supplier_deliveries
show_verifications
settlement_runs
notifications
audit_events
outbox_events
webhook_receipts
idempotency_keys
```

---

# Future security, privacy, and compliance

## Security controls

- Multi-factor authentication for privileged roles
- Passkeys where supported
- Recent-authentication requirements for financial and ownership actions
- Tenant-aware authorization on every request
- Encrypted token and secret storage
- Key rotation and revocation
- Short-lived signed asset URLs
- Malware and content-type scanning
- Webhook signature validation
- OAuth state, nonce, PKCE where applicable, and redirect allowlists
- CSRF protection
- Rate limits and abuse controls
- Idempotency for payments, refunds, ticket issuance, publishing, and releases
- Immutable audit log
- Database backups and tested restoration
- Dependency, container, secret, and infrastructure scanning
- Incident response and breach notification procedures

## Privacy controls

- Consent records by purpose and channel
- Data minimization
- Regional cookie and tracking controls
- Marketing opt-in and unsubscribe
- Data export and deletion workflows
- Retention schedules
- Restricted access to identity and financial information
- Hashing or tokenization of identifiers sent to advertising platforms where permitted
- Separation of transactional and marketing communication preferences

## Marketplace and financial controls

- KYC/KYB through the payment or regulated partner
- Sanctions and fraud screening where required
- Supplier identity and insurance verification
- Chargeback and dispute reserves
- Double-entry reconciliation
- Payout holds and exception review
- No unsupported escrow representation
- Counsel-approved campaign, ticket, cancellation, refund, and supplier terms

## Safety and accessibility

- Verified legal capacity
- Accessibility information and ticket allocation
- Emergency and medical planning
- Age and alcohol policy
- Security requirements
- Insurance and permit gates
- Content accessibility, captions, keyboard navigation, and screen-reader support
- WCAG-aligned public and operational interfaces

---

# Future observability and operations

## Required telemetry

- API latency and errors
- Queue depth and job age
- Workflow state and stuck executions
- Payment webhook lag
- Ledger reconciliation differences
- Social token health
- Publishing success and rejection rates
- Render duration and failure reason
- Ticket inventory consistency
- Duplicate scan attempts
- Event readiness blockers
- Supplier delivery exceptions
- Refund and dispute rates

## Correlation

Every request, workflow, external call, domain event, and ledger action should carry:

```text
request_id
correlation_id
causation_id
organization_id
event_id
actor_id
automation_id
```

## Alert priorities

```text
P0: payment integrity, ticket oversell, security breach, unsafe event state
P1: settlement blocked, widespread login or checkout failure
P2: publishing failure, delayed render, supplier integration issue
P3: noncritical analytics or reporting degradation
```

---

# Future testing strategy

## Unit tests

- Threshold calculations
- State transitions
- Match scoring
- Ticket inventory and hold expiration
- Fee and refund calculations
- Ledger posting
- Budget rules
- Payout evidence rules

## Property-based tests

- Money is conserved across ledger entries
- Ticket inventory never becomes negative
- A ticket has one current owner
- Duplicate webhooks do not duplicate effects
- A campaign cannot become live without required confirmation gates
- A payout cannot exceed approved allocation

## Integration tests

- OAuth and token refresh
- Stripe or payment-adapter webhooks
- E-signature callbacks
- Meta, YouTube, TikTok, email, and SMS adapters
- Object storage and signed URLs
- Search indexing

## Contract tests

Version and verify external API payloads and internal domain-event schemas.

## End-to-end tests

```text
Create user
→ create campaign
→ collect support
→ reach threshold
→ match band and venue
→ sign agreements
→ convert reservations
→ sell ticket
→ publish content
→ scan ticket
→ verify show
→ refund or settle
```

## Failure tests

- Duplicate payment webhook
- Social token revoked
- Video upload interrupted
- Venue cancels after ticket sales start
- Equipment supplier fails before load-in
- Database failover during checkout
- Scanner offline and later synchronized
- Payment dispute during settlement

## Security tests

- Tenant isolation
- Privilege escalation
- OAuth redirect abuse
- Token leakage
- Webhook replay
- File-upload attacks
- Rate-limit bypass
- IDOR and mass-assignment testing

---

# Future repository architecture

A possible future repository layout:

```text
apps/
  web/
  scanner-pwa/
  admin-console/

backend/
  config/
  identity/
  organizations/
  campaigns/
  events/
  artists/
  venues/
  rentals/
  marketplace/
  contracts/
  ticketing/
  payments/
  ledger/
  marketing/
  media/
  production/
  notifications/
  analytics/
  audit/
  integrations/

workers/
  transactional/
  social-publishing/
  media-rendering/
  analytics-ingestion/
  reconciliation/

infrastructure/
  docker/
  terraform/
  kubernetes/
  monitoring/

packages/
  api-client/
  domain-events/
  design-system/
  shared-types/
  media-templates/

docs/
  architecture/
  adr/
  api/
  security/
  compliance/
  runbooks/
```

The initial implementation can remain in the existing Django and React structure while adopting these boundaries gradually.

---

# Future delivery roadmap

## Future Phase 1 — Account foundation

- User, Band, and Venue signup choices
- One login with multiple organizations and roles
- Google and Facebook sign-on
- Separate YouTube and Meta Business authorization
- Verification and connected-account health
- Brand kit and profile onboarding

## Future Phase 2 — Autonomous media MVP

- Campaign brand generation
- One reusable vertical-video template
- Local or approved script, narration, and caption pipeline
- FFmpeg rendering workers
- YouTube upload and scheduling
- Facebook Page and Instagram publishing where approved
- Approval modes and audit history

## Future Phase 3 — Ticketing

- Ticket types and capacity
- Checkout and payments
- QR tickets
- Scanner PWA
- Transfers, waitlist, and refunds
- Ticket milestone marketing

## Future Phase 4 — Venue marketplace

- Venue accounts and listings
- Spaces, capacity, technical specifications, and calendars
- Matching and standardized quote requests
- Holds, contracts, and deposits

## Future Phase 5 — Rental and professional marketplace

- Rental company accounts
- Inventory and packages
- Rider and venue-gap requirement generation
- Quotes, reservations, delivery, return, and damage workflow
- Event professional profiles and matching

## Future Phase 6 — Demand-to-production automation

- Durable event workflow
- Artist and venue negotiation boundaries
- E-signature
- Production checklist and show-readiness gates
- Sponsor matching
- Controlled payment milestones

## Future Phase 7 — Full marketing autopilot

- Meta Ads and Lead Ads where approved
- Messenger assistant
- TikTok and additional channel adapters
- Creative testing and deterministic budget control
- Multi-touch attribution and funnel optimization

## Future Phase 8 — Settlement and marketplace scale

- Full double-entry ledger
- Reconciliation
- Supplier payouts
- Show verification
- Event settlement
- Reviews, reputation, dispute management
- Multi-region and high-availability scaling

---

# Future definition of “fully automated”

The platform can automate all routine, rule-driven tasks after one-time customer authorization:

- Account and workspace provisioning
- Brand and campaign asset generation
- Content planning, rendering, scheduling, and publishing
- Demand collection and milestone detection
- Matching and quote requests
- Standardized offer comparison
- Contract preparation and signature routing
- Ticket creation, sale, delivery, waitlist, scanning, and eligible refunds
- Equipment requirement calculation and rental coordination
- Operational checklists and notifications
- Marketing budget optimization inside limits
- Reconciliation and report generation

The following remain explicit authorization or exception gates:

- OAuth consent and channel selection
- Identity and bank verification
- Brand approval when required
- Contract signature
- Actions outside negotiation limits
- Material date, venue, artist, capacity, or refund-policy changes
- Safety, insurance, permit, legal, copyright, fraud, and dispute exceptions
- Final releases where regulation or customer policy requires approval

The target product experience is therefore:

> **One event idea becomes a branded, promoted, demand-validated, matched, contracted, ticketed, produced, verified, and settled live event—with people involved only for authorization, signatures, compliance, safety, and exceptional decisions.**

---

# Future integration references

Official documentation should be rechecked during implementation because platform permissions, API versions, quotas, and review requirements change.

- Google and YouTube OAuth for server-side applications: https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
- YouTube Data API: https://developers.google.com/youtube/v3/docs
- YouTube video uploads: https://developers.google.com/youtube/v3/docs/videos/insert
- YouTube custom thumbnails: https://developers.google.com/youtube/v3/docs/thumbnails/set
- Stripe Connect manual payouts and escrow terminology: https://docs.stripe.com/connect/manual-payouts
- Stripe Connect separate charges and transfers: https://docs.stripe.com/connect/separate-charges-and-transfers
- Stripe payment-method setup for later payments: https://docs.stripe.com/payments/setup-intents
- TikTok Login Kit: https://developers.tiktok.com/doc/login-kit-overview/
- TikTok Content Posting: https://developers.tiktok.com/products/content-posting-api/
- Meta developer documentation: https://developers.facebook.com/docs/

---

# Final future distinction

Traditional event software begins after the risky decisions have already been made:

```text
Book the band and venue
→ spend money
→ list tickets
→ hope demand exists
```

The future platform begins with evidence:

```text
Plant the seed
→ prove local demand
→ verify commitments
→ assemble the band, venue, rentals, professionals, and sponsors
→ sign contracts
→ sell and validate tickets
→ automate marketing and production
→ verify the show
→ reconcile and settle
```

That is the long-term Open Concert / VibesMeet opportunity: a complete operating system and marketplace for making live events happen from verified audience demand.

---

# VibesMeet integration and missing-module companion blueprint

The detailed module-by-module gap analysis, product ownership boundary, lifecycle, handoff contract, reservation-conversion model, proposed webhook events, data-model additions, UI modules, security controls, and phased delivery plan are maintained in:

- [`docs/VIBESMEET_INTEGRATION_AND_MODULE_BLUEPRINT.md`](docs/VIBESMEET_INTEGRATION_AND_MODULE_BLUEPRINT.md)
- [`docs/openapi/vibesmeet-bridge.openapi.yaml`](docs/openapi/vibesmeet-bridge.openapi.yaml)
- [`docs/schemas/vibesmeet-event-handoff.schema.json`](docs/schemas/vibesmeet-event-handoff.schema.json)
- [`docs/schemas/vibesmeet-webhook-envelope.schema.json`](docs/schemas/vibesmeet-webhook-envelope.schema.json)
- [`backend/integrations/vibesmeet/`](backend/integrations/vibesmeet/)

This companion blueprint explicitly adds modules that were previously missing or not deep enough, including identity federation, external-resource mapping, capability negotiation, campaign moderation, duplicate merging, preference polling, confidence-adjusted demand, target economics, artist offers, venue holds, tour routing, rider parsing, travel and hospitality, compliance, readiness gates, reservation-to-ticket conversion, ticket cohorts, cancellation/reschedule orchestration, incident management, sponsor activation evidence, reconciliation, and the post-event demand learning loop.
