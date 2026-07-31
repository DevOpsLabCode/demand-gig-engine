# Gig Engine Social Authentication

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


The gig engine uses Django sessions plus `django-allauth` as a provider-neutral OAuth broker. This keeps one local user identity while supporting Google, Facebook, Instagram, and TikTok accounts.

## User account types

- Fan
- Band / artist
- Venue
- Organizer / promoter
- Equipment rental
- Sponsor

A user can link multiple social accounts to one Django user. Campaigns, pledges, and sponsor commitments retain nullable user references so existing anonymous flows remain compatible.

## Provider callback URLs

| Provider | Callback URL |
|---|---|
| Google | `https://gig.example.com/accounts/google/login/callback/` |
| Facebook | `https://gig.example.com/accounts/facebook/login/callback/` |
| Instagram | `https://gig.example.com/accounts/instagram/login/callback/` |
| TikTok | `https://gig.example.com/accounts/tiktok/login/callback/` |

TikTok requires an HTTPS callback and app review for production access. Instagram capabilities depend on the Meta product and permissions approved for the app.

## Environment variables

```dotenv
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
FACEBOOK_OAUTH_CLIENT_ID=
FACEBOOK_OAUTH_CLIENT_SECRET=
INSTAGRAM_OAUTH_CLIENT_ID=
INSTAGRAM_OAUTH_CLIENT_SECRET=
TIKTOK_OAUTH_CLIENT_KEY=
TIKTOK_OAUTH_CLIENT_SECRET=
LOGIN_REDIRECT_URL=https://gig.example.com
CSRF_TRUSTED_ORIGINS=https://gig.example.com
SOCIAL_AUTH_ALLOWED_PROVIDERS=google,facebook,instagram,tiktok
ALLAUTH_TRUSTED_PROXY_COUNT=2
```

In AWS, store secrets in Secrets Manager and inject them into ECS task definitions. Do not create `SocialApp` database rows containing production secrets.

## API endpoints

- `GET /api/auth/config/` — current session, enabled providers, CSRF token, account types
- `GET /api/auth/profile/` — authenticated user profile
- `PATCH /api/auth/profile/` — account type and profile updates
- `POST /api/auth/logout/` — session logout

Provider handshakes use allauth routes under `/accounts/` and are initiated using POST plus CSRF protection.

## Authorization rules

- Anyone may browse campaigns and submit a fan pledge or sponsorship commitment.
- Authentication is required to create a campaign.
- Only the campaign owner or Django staff can launch, edit, confirm, finalize, refund, publish to Facebook, or delete it.
- Provider access tokens are not stored during login. Publishing permissions must use a separate explicit account-connection flow.

## Production routing

Use one public host such as `https://gig.example.com`. CloudFront serves the React application and routes `/api/*`, `/accounts/*`, `/admin/*`, and `/share/*` to the Django ALB origin. This same-site design simplifies secure session cookies, CSRF, and OAuth callbacks.

`ALLAUTH_TRUSTED_PROXY_COUNT` must match the verified CloudFront/ALB proxy chain. The recommended starting value in this architecture is `2`, but confirm the actual `X-Forwarded-For` chain before enabling it.

Instagram login must remain disabled until the Meta app product, permissions, and callback flow have been verified against the currently approved Instagram Login API. TikTok requires an approved Login Kit application and HTTPS redirect URI.

## Flow diagram

- SVG: [`social-auth-flow.svg`](social-auth-flow.svg)
- PNG: [`social-auth-flow.png`](social-auth-flow.png)
- Graphviz source: [`social-auth-flow.dot`](social-auth-flow.dot)

## Runtime and health checks

The backend exposes `GET /api/health/` for ALB, ECS, and container readiness checks. The production backend image runs Gunicorn; Docker Compose intentionally overrides it with Django `runserver` for local development.

Docker Compose passes all four provider credential pairs into the backend when they are defined in the root `.env`. A provider is returned as enabled by `/api/auth/config/` only when it is allowlisted, has both credentials, and its Allauth login route is registered.

## Test coverage

`backend/gigs/tests/test_auth.py` covers anonymous and authenticated configuration, CSRF token delivery, provider enablement and URL resolution, linked social accounts, avatar/profile synchronization, profile validation, login-required campaign creation, owner/staff authorization, and authenticated pledge/sponsor attribution. Run `./scripts/run_full_tests.sh` locally or push a new commit to execute the GitHub Python matrix.
