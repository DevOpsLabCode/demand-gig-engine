from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from gigs.models import DemandCampaign, GoalType
from gigs.services import launch_campaign


class Command(BaseCommand):
    help = "Create and launch a sample demand-driven gig campaign."

    def handle(self, *args, **options):
        campaign, created = DemandCampaign.objects.get_or_create(
            slug="bring-band-x-to-new-york",
            defaults={
                "title": "Bring Band X to New York",
                "pitch": "Commit now. We confirm the artist and venue only after the audience proves demand.",
                "artist_name": "Band X",
                "city": "New York",
                "country": "United States",
                "deadline": timezone.now() + timedelta(days=30),
                "goal_type": GoalType.BOTH,
                "supporter_target": 500,
                "amount_target": Decimal("25000.00"),
                "suggested_deposit": Decimal("25.00"),
                "organizer_name": "Open Concert Community",
                "organizer_email": "organizer@example.com",
            },
        )
        if created:
            launch_campaign(campaign.id)
            self.stdout.write(self.style.SUCCESS(f"Created {campaign.slug}"))
        else:
            self.stdout.write(f"Campaign already exists: {campaign.slug}")
