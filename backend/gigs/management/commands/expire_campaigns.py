# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provides a one-shot Django command that fails overdue campaigns which missed their threshold and triggers refundable-deposit processing.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Provides a one-shot Django command that fails overdue campaigns which missed their threshold and triggers refundable-deposit processing.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.core.management.base import BaseCommand
from gigs.services import expire_due_campaigns


class Command(BaseCommand):
    """
    Expose overdue-campaign expiry and refundable-deposit processing as a one-shot Django management command.
    """
    help = "Fail expired campaigns that missed their target and refund deposits."

    def handle(self, *args, **options):
        """
        Expire overdue campaigns that missed their threshold and report how many were processed.
        
        Args:
            *args: Additional positional arguments forwarded to the underlying implementation.
            **options: Additional keyword arguments forwarded to the underlying implementation.
        """
        count = expire_due_campaigns()
        self.stdout.write(self.style.SUCCESS(f"Processed {count} expired campaign(s)."))
