from django.core.management.base import BaseCommand
from gigs.services import expire_due_campaigns


class Command(BaseCommand):
    help = "Fail expired campaigns that missed their target and refund deposits."

    def handle(self, *args, **options):
        count = expire_due_campaigns()
        self.stdout.write(self.style.SUCCESS(f"Processed {count} expired campaign(s)."))
