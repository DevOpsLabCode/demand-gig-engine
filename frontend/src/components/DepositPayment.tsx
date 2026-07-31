/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Confirms a Stripe PaymentIntent for a refundable supporter deposit and reports completion to the campaign card.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { FormEvent, useState } from "react";
import { PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";

/**
 * Receive the callback invoked after Stripe confirms the supporter deposit.
 */
interface Props {
  onSuccess: () => Promise<void>;
}

/**
 * Render Stripe PaymentElement, prevent duplicate submission, and display provider validation or confirmation errors.
 */
export function DepositPayment({ onSuccess }: Props) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  /** Confirm the existing PaymentIntent without creating a second pledge or charge. */
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setBusy(true);
    setError("");
    const result = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: window.location.href },
      redirect: "if_required",
    });
    if (result.error) {
      setError(result.error.message ?? "Payment could not be completed.");
    } else {
      await onSuccess();
    }
    setBusy(false);
  }

  return (
    <form className="stripe-box" onSubmit={submit}>
      <PaymentElement />
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={!stripe || busy}>{busy ? "Completing…" : "Complete refundable deposit"}</button>
    </form>
  );
}
