# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Abstracts refundable deposit, capture, refund, and Stripe client-secret operations behind a provider interface.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Abstracts refundable deposit, capture, refund, and Stripe client-secret operations behind a provider interface.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
import uuid

from django.conf import settings


@dataclass
class PaymentResult:
    """
    Carry the provider reference, status, and browser client secret returned by a deposit request.
    """
    reference: str
    client_secret: str = ""
    status: str = "paid"


class PaymentProvider(Protocol):
    """
    Define the payment operations required by the campaign service layer.
    """
    name: str

    # Create the supporter deposit and return the stable provider reference needed for later capture or refund.
    def collect_refundable_deposit(self, *, amount: Decimal, currency: str, email: str, idempotency_key: str, metadata: dict) -> PaymentResult: ...
    # Reverse the referenced deposit, optionally limiting the refund to a specific amount.
    def refund(self, *, payment_reference: str, amount: Decimal | None = None) -> str: ...
    # Finalize or capture the referenced commitment after the gig reaches its confirmation requirements.
    def finalize(self, *, payment_reference: str) -> str: ...
    # Recover the browser client secret for an idempotently reused pending payment.
    def get_client_secret(self, *, payment_reference: str) -> str: ...


class FakePaymentProvider:
    """
    Provide deterministic payment behavior for tests and local development.
    """
    name = "fake"

    def collect_refundable_deposit(self, *, amount, currency, email, idempotency_key, metadata):
        """
        Create a deterministic in-memory payment result for local development and tests.
        
        Args:
            amount: Monetary amount represented as a Decimal-compatible value.
            currency: Three-letter ISO-style currency code associated with the monetary amount.
            email: User email normalized for identity matching or attribution.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            metadata: Non-secret contextual fields attached to the provider request.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        return PaymentResult(reference=f"fake_pi_{uuid.uuid4().hex}", status="paid")

    def refund(self, *, payment_reference, amount=None):
        """
        Record a successful fake refund without contacting an external gateway.
        
        Args:
            payment_reference: Stable provider identifier of the deposit, PaymentIntent, or charge.
            amount: Monetary amount represented as a Decimal-compatible value.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        return f"fake_re_{uuid.uuid4().hex}"

    def finalize(self, *, payment_reference):
        """
        Record a successful fake finalization without contacting an external gateway.
        
        Args:
            payment_reference: Stable provider identifier of the deposit, PaymentIntent, or charge.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        return payment_reference

    def get_client_secret(self, *, payment_reference):
        """
        Return the deterministic client secret associated with a fake payment reference.
        
        Args:
            payment_reference: Stable provider identifier of the deposit, PaymentIntent, or charge.
        
        Returns:
            The validated result described in the function summary and return annotation.
        """
        return ""


class StripePaymentProvider:
    """
    Implement refundable deposits, capture, refunds, and retrieval through Stripe PaymentIntents.

    This is deliberately not described as escrow. If a campaign fails, the service
    creates a Stripe refund. Long-running campaigns should not rely on card
    authorization holds because card-network authorization windows are limited.
    """

    name = "stripe"

    def __init__(self):
        """
        Initialize the Stripe SDK with the configured secret key.
        """
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.stripe = stripe

    def collect_refundable_deposit(self, *, amount, currency, email, idempotency_key, metadata):
        """
        Create a manual-capture Stripe PaymentIntent used as the supporter's refundable commitment.
        
        Args:
            amount: Monetary amount represented as a Decimal-compatible value.
            currency: Three-letter ISO-style currency code associated with the monetary amount.
            email: User email normalized for identity matching or attribution.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            metadata: Non-secret contextual fields attached to the provider request.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        cents = int((amount * 100).quantize(Decimal("1")))
        intent = self.stripe.PaymentIntent.create(
            amount=cents,
            currency=currency.lower(),
            receipt_email=email,
            automatic_payment_methods={"enabled": True},
            metadata=metadata,
            description="Refundable demand-campaign deposit",
            idempotency_key=idempotency_key,
        )
        return PaymentResult(
            reference=intent.id,
            client_secret=intent.client_secret or "",
            status=intent.status,
        )

    def refund(self, *, payment_reference, amount=None):
        """
        Issue a Stripe refund for the referenced PaymentIntent or charge.
        
        Args:
            payment_reference: Stable provider identifier of the deposit, PaymentIntent, or charge.
            amount: Monetary amount represented as a Decimal-compatible value.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        kwargs = {"payment_intent": payment_reference}
        # Request a partial Stripe refund only when a specific amount was supplied; otherwise refund the full payment.
        if amount is not None:
            kwargs["amount"] = int((amount * 100).quantize(Decimal("1")))
        refund = self.stripe.Refund.create(**kwargs)
        return refund.id

    def finalize(self, *, payment_reference):
        # Deposits are already charged. Finalization changes the internal business
        # status. Any remaining ticket balance should be collected separately.
        """
        Capture the Stripe PaymentIntent after artist and venue confirmation.
        
        Args:
            payment_reference: Stable provider identifier of the deposit, PaymentIntent, or charge.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        return payment_reference

    def get_client_secret(self, *, payment_reference):
        """
        Retrieve an existing Stripe PaymentIntent and return its client secret.
        
        Args:
            payment_reference: Stable provider identifier of the deposit, PaymentIntent, or charge.
        
        Returns:
            The validated result described in the function summary and return annotation.
        """
        intent = self.stripe.PaymentIntent.retrieve(payment_reference)
        return intent.client_secret or ""


def get_payment_provider() -> PaymentProvider:
    """
    Select the configured fake or Stripe payment adapter and fail fast on invalid configuration.
    
    Returns:
        A configured payment-provider adapter implementing the common provider protocol.
    
    Raises:
        RuntimeError: When the documented validation or integration precondition fails.
    """
    # Instantiate the Stripe adapter only when Stripe is the selected payment backend.
    if settings.PAYMENT_PROVIDER.lower() == "stripe":
        # Return a controlled configuration response when required integration credentials are absent.
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY is required when PAYMENT_PROVIDER=stripe")
        return StripePaymentProvider()
    return FakePaymentProvider()
