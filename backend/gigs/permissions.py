# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines object-level authorization for campaign owners and privileged staff users.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Defines object-level authorization for campaign owners and privileged staff users.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from rest_framework.permissions import BasePermission


class IsCampaignOwnerOrStaff(BasePermission):
    """Protect campaign mutations while allowing owners and privileged staff."""

    message = "Only the campaign owner or an administrator can perform this action."

    def has_object_permission(self, request, view, obj):
        """
        Allow campaign mutations only to the owning organizer or privileged staff.
        
        Args:
            request: Incoming Django/DRF request, including the authenticated user and payload.
            view: DRF view requesting the object-level permission decision.
            obj: Model object against which object-level permission is evaluated.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        return bool(request.user.is_staff or obj.owner_id == request.user.id)
