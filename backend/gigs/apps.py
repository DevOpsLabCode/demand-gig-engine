# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the Django application and loads auxiliary models and signal handlers at the correct registry stages.

"""Django application configuration for the demand-gig domain."""

from django.apps import AppConfig


class GigsConfig(AppConfig):
    """Register the gigs application, auxiliary models, and signal handlers."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "gigs"

    def import_models(self):
        """Load primary and modular Phase 1, Phase 1B, and Phase 2 models."""

        super().import_models()
        from . import (  # noqa: F401
            campaign_preference_models,
            campaign_review_models,
            role_models,
        )

    def ready(self):
        """Load signals and extend runtime status validation with Phase 1B states."""

        from . import signals  # noqa: F401

        campaign = self.get_model("DemandCampaign")
        status_field = campaign._meta.get_field("status")
        existing = list(status_field.choices)
        existing_values = {value for value, _label in existing}
        phase_1b_choices = [
            ("pending_review", "Pending review"),
            ("approved", "Approved"),
            ("threshold_reached", "Threshold reached"),
            ("feasibility_review", "Feasibility review"),
            ("conditionally_ready", "Conditionally ready"),
            ("ready", "Ready"),
            ("handed_off", "Handed off"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
            ("not_viable", "Not viable"),
            ("refund_pending", "Refund pending"),
        ]
        status_field.choices = existing + [
            choice for choice in phase_1b_choices if choice[0] not in existing_values
        ]
