/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Initializes Stripe.js and exposes the configured publishable-key client to payment components.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { loadStripe } from "@stripe/stripe-js";

/** Read only Stripe's browser-safe publishable key; the secret key remains on the backend. */
const publishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY ?? "";
/** Load one reusable Stripe.js client, or expose null so payment UI stays disabled when no key is configured. */
export const stripePromise = publishableKey ? loadStripe(publishableKey) : null;
