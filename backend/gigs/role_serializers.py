# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Validates role requests and serializes role definitions and verification assignments.

"""DRF serializers for multiple-role selection and verification."""

from rest_framework import serializers

from .role_models import Role, RoleCode, UserRole


class RoleSerializer(serializers.ModelSerializer):
    """Expose safe role-catalog fields to authenticated users."""

    class Meta:
        model = Role
        fields = [
            "code",
            "display_name",
            "description",
            "requires_verification",
        ]


class UserRoleSerializer(serializers.ModelSerializer):
    """Expose one role assignment without leaking reviewer account details."""

    role = RoleSerializer(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    user_display_name = serializers.SerializerMethodField()
    verified_by_id = serializers.IntegerField(read_only=True)

    def get_user_display_name(self, obj):
        profile = getattr(obj.user, "gig_profile", None)
        return (
            (profile.display_name if profile else "")
            or obj.user.get_full_name()
            or obj.user.get_username()
        )

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user_id",
            "user_display_name",
            "role",
            "organization_name",
            "profile_data",
            "verification_status",
            "verified_by_id",
            "verified_at",
            "created_at",
            "updated_at",
        ]


class RoleRequestSerializer(serializers.Serializer):
    """Validate a self-service request for a non-administrator role."""

    role_code = serializers.ChoiceField(
        choices=[
            choice
            for choice in RoleCode.values
            if choice != RoleCode.ADMINISTRATOR
        ]
    )
    organization_name = serializers.CharField(
        max_length=180,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    profile_data = serializers.JSONField(required=False, default=dict)

    def validate_profile_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Role profile data must be a JSON object.")
        return value
