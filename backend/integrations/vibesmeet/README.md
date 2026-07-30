# VibesMeet integration bridge

This package is a **contract-first scaffold**, not a claim that the proposed endpoint paths are already available publicly.

It provides:

- a dependency-free HTTP client;
- typed event-handoff and reservation-claim payloads;
- HMAC webhook signing and verification;
- proposed event names;
- strict validation for ticket inventory, dates, credits, and revenue splits.

Before production use:

1. Confirm VibesMeet authentication, endpoints, scopes, rate limits, and webhook signatures.
2. Replace or configure proposed paths in `client.py`.
3. Store tokens and webhook secrets in a secrets manager.
4. Add Django persistence for outbox deliveries, webhook inbox, external resource mappings, conflicts, and reconciliation.
5. Process calls asynchronously with retries and dead-letter handling.
6. Require readiness and authorization before creating or publishing an event.
7. Reconcile reservation credits to VibesMeet orders and refunds.

See:

- `docs/VIBESMEET_INTEGRATION_AND_MODULE_BLUEPRINT.md`
- `docs/openapi/vibesmeet-bridge.openapi.yaml`
- `docs/schemas/vibesmeet-event-handoff.schema.json`
- `docs/schemas/vibesmeet-webhook-envelope.schema.json`
