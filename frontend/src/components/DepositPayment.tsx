import { FormEvent, useState } from "react";
import { PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";

interface Props {
  onSuccess: () => Promise<void>;
}

export function DepositPayment({ onSuccess }: Props) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
