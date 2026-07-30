from rest_framework.permissions import BasePermission


class IsCampaignOwnerOrStaff(BasePermission):
    """Allow campaign management only to its authenticated owner or staff."""

    message = "Only the campaign owner or an administrator can perform this action."

    def has_object_permission(self, request, view, obj):
        return bool(request.user.is_staff or obj.owner_id == request.user.id)
