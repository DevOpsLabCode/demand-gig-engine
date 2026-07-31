# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the Django application and loads signal handlers when the application registry is ready.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Declares the Django application and loads signal handlers when the application registry is ready.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.apps import AppConfig


class GigsConfig(AppConfig):
    """
    Register the gigs Django application and load signal handlers only after the application registry is ready.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "gigs"

    def ready(self):
        """
        Import signal handlers after Django finishes loading the application registry.
        """
        from . import signals  # noqa: F401
