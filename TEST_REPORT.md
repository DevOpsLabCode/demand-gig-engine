# Validation and Test Report

**Project:** Demand-Driven Gig Creation MVP  
**Validation date:** July 29, 2026  
**Source tested:** Uploaded `demand-gig-mvp(1) (1).zip`

## Executive result

The package passed all dependency-free structural, syntax, document, image, configuration, and archive-integrity checks available in the execution environment. Several defects found during review were corrected before repackaging.

Full framework execution was attempted but could not be completed inside this sandbox because its Python and npm package registries do not contain the required Django, React, Vite, or Stripe packages, and Docker is not installed. The project includes `scripts/run_full_tests.sh` so the complete runtime suite can be executed in a normal internet-connected development environment.

## Verified checks

| Area | Result | What was verified |
|---|---|---|
| Uploaded ZIP | PASS | `unzip -t` reported no compressed-data errors. |
| Python source | PASS | Every backend `.py` file parsed and compiled successfully. |
| TypeScript source | PASS | All `.ts` and `.tsx` files passed TypeScript checking using local declarations for unavailable third-party packages. |
| JSON | PASS | `package.json` and `tsconfig.json` parsed successfully. |
| Docker Compose | PASS | YAML parsed; database, backend, and frontend services are present; backend waits for database health. |
| Migration structure | PASS | Sequential migrations `0001` through `0003`; campaign-scoped pledge idempotency exists in both model and migration. |
| Frontend/backend API contract | PASS | Campaign, pledge, sponsor, Facebook configuration/login/Page/share endpoints match the frontend request paths and slug lookup. |
| Screenshots | PASS | All three required PNGs have valid PNG headers and nonzero dimensions. |
| Combined PDF | PASS | PDF opens, is not encrypted, has 26 pages, embedded fonts, a valid EOF marker, and rendered successfully to 26 PNG pages. |
| Secrets scan | PASS | No live Stripe secret, webhook secret, Facebook access token, or private key was found in the packaged source. |

## Runtime tests attempted but environment-blocked

| Test | Status | Reason |
|---|---|---|
| `python manage.py check` | BLOCKED | Django and Django REST Framework are unavailable in the sandbox registry. |
| Django migrations against SQLite/PostgreSQL | BLOCKED | Same missing Python dependencies; PostgreSQL service cannot be started without Docker. |
| Django unit tests | BLOCKED | Same missing Python dependencies. |
| `npm install` and production Vite build | BLOCKED | The sandbox npm registry returns `404` for React, Vite, TypeScript, and Stripe packages. |
| Docker Compose end-to-end startup | BLOCKED | Docker CLI/daemon is not installed in the sandbox. |
| Live Stripe webhook/payment/refund test | NOT RUN | Requires Stripe test credentials, outbound connectivity, and a webhook tunnel. |
| Live Meta Login/Page publishing/Conversions API test | NOT RUN | Requires a configured Meta app, approved permissions, access tokens, and outbound connectivity. |

These blocked checks are not reported as passes. Run `./scripts/run_full_tests.sh` in a normal development environment to execute them.

## Defects found and corrected

1. **Cross-campaign idempotency collision:** pledge idempotency keys were globally unique and could return a pledge from another campaign. They are now unique per campaign, with migration `0003_scope_pledge_idempotency.py`.
2. **Stripe retry usability:** a repeated pending Stripe request could lose its client secret. The payment provider can now retrieve it from the existing PaymentIntent.
3. **Incomplete failure cleanup:** nonfinancial attendance commitments remained active after campaign failure. They are now canceled.
4. **Sponsor cleanup:** pledged sponsors are canceled when a campaign fails; paid/finalized sponsor commitments enter the refund workflow when a payment reference exists.
5. **Sponsor finalization:** sponsor commitments are marked finalized when the campaign becomes a live event.
6. **Webhook state regression:** delayed Stripe events could overwrite terminal pledge states. Webhook updates now apply only while a pledge is pending.
7. **Campaign goal validation:** invalid supporter or financial thresholds are rejected by the API serializer before launch.
8. **Currency normalization and display:** currency codes are normalized to uppercase and campaign totals use currency-aware frontend formatting.
9. **Facebook readiness flag:** Facebook connection is reported as enabled only when both the App ID and App Secret are configured.

## Automated backend test coverage included

The packaged Django test suite covers:

- Draft launch and collecting state
- Combined supporter/money threshold transition
- Artist and venue confirmation gates
- Final conversion into a live event
- Paid pledge refund
- Cancellation of nonfinancial attendance commitments
- Sponsor cancellation and finalization
- Campaign-scoped idempotency
- Sponsor-triggered money threshold
- Early confirmation rejection
- Expired campaign launch rejection
- Unique slug generation
- Facebook share-link encoding and attribution
- Currency normalization
- Invalid financial target rejection

## Remaining production risks

This is a reference MVP, not a production authorization or payments system. Before deployment, add VibesMeet identity and role-based permissions, organizer ownership checks, rate limiting, asynchronous payment/refund jobs, durable idempotency records for Meta events, encrypted token storage, double-entry payout accounting, audit monitoring, privacy consent, and legal review of deposit/refund terms.

## Reproduce the complete test suite

```bash
unzip demand-gig-mvp-tested.zip
cd demand-gig-mvp
./scripts/run_full_tests.sh
```

For an end-to-end Docker smoke test after the script passes:

```bash
docker compose up --build
# In another terminal:
curl -f http://localhost:8000/api/campaigns/
curl -f http://localhost:5173/
```
