# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines the supported VibesMeet event names and event-category constants.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""Proposed VibesMeet webhook event names.

These names are a contract proposal and must be aligned with VibesMeet before
production use.
"""

EVENT_DRAFT_CREATED = "vibesmeet.event.draft_created"
EVENT_UPDATED = "vibesmeet.event.updated"
EVENT_PUBLISHED = "vibesmeet.event.published"
EVENT_RESCHEDULED = "vibesmeet.event.rescheduled"
EVENT_CANCELED = "vibesmeet.event.canceled"
RESERVATION_CLAIM_CREATED = "vibesmeet.reservation_claim.created"
RESERVATION_CLAIM_CLAIMED = "vibesmeet.reservation_claim.claimed"
RESERVATION_CLAIM_EXPIRED = "vibesmeet.reservation_claim.expired"
ORDER_PAID = "vibesmeet.order.paid"
ORDER_REFUNDED = "vibesmeet.order.refunded"
ORDER_CHARGEBACK_OPENED = "vibesmeet.order.chargeback_opened"
ATTENDANCE_VERIFIED = "vibesmeet.attendance.verified"
PAYOUT_PENDING = "vibesmeet.payout.pending"
PAYOUT_COMPLETED = "vibesmeet.payout.completed"
PAYOUT_FAILED = "vibesmeet.payout.failed"
SPONSOR_OPPORTUNITY_UPDATED = "vibesmeet.sponsor_opportunity.updated"
SPONSOR_ACTIVATION_UPDATED = "vibesmeet.sponsor_activation.updated"
PERMISSION_REVOKED = "vibesmeet.integration.permission_revoked"

KNOWN_EVENT_TYPES = {
    value
    for name, value in globals().items()
    if name.isupper() and isinstance(value, str) and name != "KNOWN_EVENT_TYPES"
}
