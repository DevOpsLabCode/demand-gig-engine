# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the Django application and loads role models and signal handlers at the correct registry stages.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""Django application configuration for the demand-gig domain."""

from django.apps import AppConfig


class GigsConfig(AppConfig):
    """Register the gigs application, auxiliary models, and signal handlers."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "gigs"

    def import_models(self):
        """Load the primary models module and the separate multiple-role model module."""

        super().import_models()
        from . import role_models  # noqa: F401

    def ready(self):
        """Import signal handlers after Django finishes loading the model registry."""

        from . import signals  # noqa: F401
