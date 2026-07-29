from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
import uuid

from django.conf import settings


@dataclass
class PaymentResult:
    reference: str
    client_secret: str = ""
    status: str = "paid"


class PaymentProvider(Protocol):
    name: str

    def collect_refundable_deposit(self, *, amount: Decimal, currency: str, email: str, idempotency_key: str, metadata: dict) -> PaymentResult: ...
    def refund(self, *, payment_reference: str, amount: Decimal | None = None) -> str: ...
    def finalize(self, *, payment_reference: str) -> str: ...
    def get_client_secret(self, *, payment_reference: str) -> str: ...


class FakePaymentProvider:
    name = "fake"

    def collect_refundable_deposit(self, *, amount, currency, email, idempotency_key, metadata):
        return PaymentResult(reference=f"fake_pi_{uuid.uuid4().hex}", status="paid")

    def refund(self, *, payment_reference, amount=None):
        return f"fake_re_{uuid.uuid4().hex}"

    def finalize(self, *, payment_reference):
        return payment_reference

    def get_client_secret(self, *, payment_reference):
        return ""


class StripePaymentProvider:
    """
    Charges a refundable campaign deposit immediately.

    This is deliberately not described as escrow. If a campaign fails, the service
    creates a Stripe refund. Long-running campaigns should not rely on card
    authorization holds because card-network authorization windows are limited.
    """

    name = "stripe"

    def __init__(self):
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.stripe = stripe

    def collect_refundable_deposit(self, *, amount, currency, email, idempotency_key, metadata):
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
        kwargs = {"payment_intent": payment_reference}
        if amount is not None:
            kwargs["amount"] = int((amount * 100).quantize(Decimal("1")))
        refund = self.stripe.Refund.create(**kwargs)
        return refund.id

    def finalize(self, *, payment_reference):
        # Deposits are already charged. Finalization changes the internal business
        # status. Any remaining ticket balance should be collected separately.
        return payment_reference

    def get_client_secret(self, *, payment_reference):
        intent = self.stripe.PaymentIntent.retrieve(payment_reference)
        return intent.client_secret or ""


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER.lower() == "stripe":
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY is required when PAYMENT_PROVIDER=stripe")
        return StripePaymentProvider()
    return FakePaymentProvider()
