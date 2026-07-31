# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines validated transport dataclasses for tickets, reservations, revenue splits, and event handoff payloads.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Defines validated transport dataclasses for tickets, reservations, revenue splits, and event handoff payloads.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from .exceptions import VibesMeetValidationError


def _money(value: Decimal | str | int | float) -> str:
    """
    Normalize monetary input to a two-decimal Decimal value.
    
    Args:
        value: Input value to normalize, hash, or validate.
    
    Returns:
        The normalized, resolved, or provider-supplied string described above.
    """
    return f"{Decimal(str(value)):.2f}"


@dataclass(frozen=True)
class TicketTypePlan:
    """
    Describe one ticket tier included in the VibesMeet event handoff.
    """
    code: str
    name: str
    price: Decimal
    currency: str
    inventory: int
    sales_start: datetime | None = None
    sales_end: datetime | None = None
    reserved_for_supporters: int = 0

    def validate(self) -> None:
        """
        Validate ticket identifiers, quantities, and non-negative prices before handoff.
        
        Raises:
            VibesMeetValidationError: When the documented validation or integration precondition fails.
        """
        # Require both a stable ticket code and human-readable ticket name.
        if not self.code or not self.name:
            raise VibesMeetValidationError("Ticket code and name are required.")
        # Reject negative ticket prices while still allowing a legitimate free tier.
        if self.price < 0:
            raise VibesMeetValidationError("Ticket price cannot be negative.")
        # Reject negative inventory and reservation counts.
        if self.inventory < 0 or self.reserved_for_supporters < 0:
            raise VibesMeetValidationError("Ticket inventory cannot be negative.")
        # Prevent supporter reservations from exceeding the ticket tier inventory.
        if self.reserved_for_supporters > self.inventory:
            raise VibesMeetValidationError("Reserved supporter inventory exceeds total inventory.")
        # Require a three-letter currency code so ticket and settlement values have an unambiguous unit.
        if len(self.currency) != 3:
            raise VibesMeetValidationError("Currency must be a three-letter code.")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the ticket plan into the JSON shape expected by VibesMeet.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        self.validate()
        return {
            "code": self.code,
            "name": self.name,
            "price": _money(self.price),
            "currency": self.currency.upper(),
            "inventory": self.inventory,
            "reserved_for_supporters": self.reserved_for_supporters,
            "sales_start": self.sales_start.isoformat() if self.sales_start else None,
            "sales_end": self.sales_end.isoformat() if self.sales_end else None,
        }


@dataclass(frozen=True)
class ReservationClaim:
    """
    Describe supporter inventory reserved before the final event is published.
    """
    reservation_id: str
    supporter_external_id: str | None
    supporter_email: str
    quantity: int
    credit_amount: Decimal
    currency: str
    ticket_type_code: str | None = None
    conversion_deadline: datetime | None = None
    referral_code: str = ""
    source: str = ""

    def validate(self) -> None:
        """
        Validate supporter reservation quantity and optional expiration timestamps.
        
        Raises:
            VibesMeetValidationError: When the documented validation or integration precondition fails.
        """
        # Require a stable reservation identifier for idempotent handoff and reconciliation.
        if not self.reservation_id:
            raise VibesMeetValidationError("Reservation ID is required.")
        # Require an email address so the reservation can be claimed by the intended supporter.
        if not self.supporter_email:
            raise VibesMeetValidationError("Supporter email is required.")
        # Require at least one reserved ticket.
        if self.quantity < 1:
            raise VibesMeetValidationError("Reservation quantity must be at least one.")
        # Reject a negative supporter credit amount.
        if self.credit_amount < 0:
            raise VibesMeetValidationError("Reservation credit cannot be negative.")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize a reservation claim while omitting optional values that are not set.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        self.validate()
        return {
            "reservation_id": self.reservation_id,
            "supporter_external_id": self.supporter_external_id,
            "supporter_email": self.supporter_email,
            "quantity": self.quantity,
            "credit_amount": _money(self.credit_amount),
            "currency": self.currency.upper(),
            "ticket_type_code": self.ticket_type_code,
            "conversion_deadline": self.conversion_deadline.isoformat() if self.conversion_deadline else None,
            "referral_code": self.referral_code,
            "source": self.source,
        }


@dataclass(frozen=True)
class RevenueSplit:
    """
    Describe one recipient and percentage in the event revenue allocation.
    """
    participant_external_id: str
    participant_type: str
    basis_points: int
    role: str

    def validate(self) -> None:
        """
        Validate the payout recipient and percentage boundaries.
        
        Raises:
            VibesMeetValidationError: When the documented validation or integration precondition fails.
        """
        # Require the payout participant identifier used by the remote settlement system.
        if not self.participant_external_id:
            raise VibesMeetValidationError("Split participant ID is required.")
        # Keep each revenue percentage between 0% and 100%.
        if not 0 <= self.basis_points <= 10_000:
            raise VibesMeetValidationError("Split basis points must be between 0 and 10000.")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize one revenue split using stable decimal formatting.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class EventHandoff:
    """
    Represent the validated local-to-VibesMeet event creation contract.
    """
    campaign_id: str
    campaign_version: str
    organizer_external_id: str
    title: str
    description: str
    timezone: str
    starts_at: datetime
    ends_at: datetime
    venue: dict[str, Any]
    artists: list[dict[str, Any]]
    capacity: int
    currency: str
    ticket_types: list[TicketTypePlan]
    reservation_claims: list[ReservationClaim] = field(default_factory=list)
    revenue_splits: list[RevenueSplit] = field(default_factory=list)
    sponsor_opportunity: dict[str, Any] | None = None
    attribution: dict[str, Any] = field(default_factory=dict)
    readiness: dict[str, Any] = field(default_factory=dict)
    accessibility: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Validate nested tickets, reservations, revenue splits, dates, currency, and total split percentage.
        
        Raises:
            VibesMeetValidationError: When the documented validation or integration precondition fails.
        """
        required_text = {
            "campaign_id": self.campaign_id,
            "campaign_version": self.campaign_version,
            "organizer_external_id": self.organizer_external_id,
            "title": self.title,
            "timezone": self.timezone,
        }
        missing = [name for name, value in required_text.items() if not value]
        # Report all missing required handoff fields together so callers can correct the contract in one pass.
        if missing:
            raise VibesMeetValidationError(f"Missing required handoff fields: {', '.join(missing)}")
        # Require the event end time to occur after its start time.
        if self.ends_at <= self.starts_at:
            raise VibesMeetValidationError("Event end must be after event start.")
        # Require positive venue capacity before publishing ticket inventory.
        if self.capacity < 1:
            raise VibesMeetValidationError("Event capacity must be at least one.")
        # Require at least one ticket type so the remote event has sellable or reservable inventory.
        if not self.ticket_types:
            raise VibesMeetValidationError("At least one ticket type is required.")
        # Process each `item` from `self.ticket_types` in a deterministic order.
        for item in self.ticket_types:
            item.validate()
        # Process each `claim` from `self.reservation_claims` in a deterministic order.
        for claim in self.reservation_claims:
            claim.validate()
        # Process each `split` from `self.revenue_splits` in a deterministic order.
        for split in self.revenue_splits:
            split.validate()
        total_bps = sum(split.basis_points for split in self.revenue_splits)
        # When revenue splits are supplied, require them to total exactly 100%.
        if self.revenue_splits and total_bps != 10_000:
            raise VibesMeetValidationError("Revenue splits must total exactly 10000 basis points.")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the complete event handoff contract into API-ready primitives.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        self.validate()
        return {
            "campaign_id": self.campaign_id,
            "campaign_version": self.campaign_version,
            "organizer_external_id": self.organizer_external_id,
            "title": self.title,
            "description": self.description,
            "timezone": self.timezone,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "venue": self.venue,
            "artists": self.artists,
            "capacity": self.capacity,
            "currency": self.currency.upper(),
            "ticket_types": [item.to_dict() for item in self.ticket_types],
            "reservation_claims": [item.to_dict() for item in self.reservation_claims],
            "revenue_splits": [item.to_dict() for item in self.revenue_splits],
            "sponsor_opportunity": self.sponsor_opportunity,
            "attribution": self.attribution,
            "readiness": self.readiness,
            "accessibility": self.accessibility,
            "policy": self.policy,
        }
