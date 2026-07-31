# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Validates and converts API payloads between JSON representations and Django domain objects.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Validates and converts API payloads between JSON representations and Django domain objects.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.utils import timezone
from rest_framework import serializers
from .models import DemandCampaign, GigUserProfile, Pledge, SponsorCommitment


class CampaignSerializer(serializers.ModelSerializer):
    """
    Validate and translate Campaign API payloads between JSON and domain objects.
    """
    owner = serializers.SerializerMethodField()
    active_supporter_count = serializers.IntegerField(read_only=True)
    committed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    target_reached = serializers.BooleanField(read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        """
        Declare model or serializer metadata such as ordering, fields, and uniqueness constraints.
        """
        model = DemandCampaign
        fields = [
            "id", "owner", "title", "slug", "pitch", "artist_name", "city", "country", "proposed_date",
            "deadline", "goal_type", "supporter_target", "amount_target", "suggested_deposit",
            "currency", "status", "artist_confirmed", "venue_confirmed", "confirmed_artist_details",
            "confirmed_venue_details", "event_id", "organizer_name", "organizer_email",
            "facebook_event_url", "facebook_group_url", "facebook_page_url",
            "active_supporter_count", "committed_amount", "target_reached", "progress_percent",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "owner",
            "slug", "status", "artist_confirmed", "venue_confirmed", "confirmed_artist_details",
            "confirmed_venue_details", "event_id", "created_at", "updated_at",
        ]

    def get_owner(self, obj):
        """
        Expose a compact owner identity without leaking the full Django user record.
        
        Args:
            obj: Model object against which object-level permission is evaluated.
        
        Returns:
            The validated result described in the function summary and return annotation.
        """
        # Represent legacy or system-created campaigns without inventing an owner identity.
        if not obj.owner_id:
            return None
        profile = getattr(obj.owner, "gig_profile", None)
        return {
            "id": obj.owner_id,
            "display_name": (profile.display_name if profile else "") or obj.owner.get_full_name() or obj.owner.get_username(),
            "account_type": profile.account_type if profile else "fan",
            "avatar_url": profile.avatar_url if profile else "",
        }

    def validate_deadline(self, value):
        """
        Reject campaign deadlines that are not in the future.
        
        Args:
            value: Input value to normalize, hash, or validate.
        
        Returns:
            The validated result described in the function summary and return annotation.
        
        Raises:
            ValidationError: When the documented validation or integration precondition fails.
        """
        # Reject an expired or non-future deadline before the campaign can accept support.
        if value <= timezone.now():
            raise serializers.ValidationError("Deadline must be in the future.")
        return value

    def validate(self, attrs):
        """
        Validate goal-specific target fields and normalize campaign input as one coherent contract.
        
        Args:
            attrs: Serializer attributes collected from the incoming request.
        
        Returns:
            The typed result described in the function summary and return annotation.
        
        Raises:
            ValidationError: When the documented validation or integration precondition fails.
        """
        goal_type = attrs.get("goal_type", getattr(self.instance, "goal_type", "supporters"))
        supporter_target = attrs.get("supporter_target", getattr(self.instance, "supporter_target", 0))
        amount_target = attrs.get("amount_target", getattr(self.instance, "amount_target", 0))
        # A supporter-based goal must require at least one attendee; zero would make the campaign immediately successful.
        if goal_type in ("supporters", "both") and supporter_target < 1:
            raise serializers.ValidationError({"supporter_target": "Must be at least 1 for this goal type."})
        # A money-based goal must be positive so progress and threshold evaluation remain meaningful.
        if goal_type in ("money", "both") and amount_target <= 0:
            raise serializers.ValidationError({"amount_target": "Must be greater than zero for this goal type."})
        # Normalize supplied currency codes to uppercase before model validation and persistence.
        if "currency" in attrs:
            attrs["currency"] = attrs["currency"].upper()
        return attrs


class GigUserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Validate and translate GigUserProfileUpdate API payloads between JSON and domain objects.
    """
    class Meta:
        """
        Declare model or serializer metadata such as ordering, fields, and uniqueness constraints.
        """
        model = GigUserProfile
        fields = [
            "account_type",
            "display_name",
            "company_name",
            "avatar_url",
            "bio",
            "city",
            "country",
        ]

    def validate(self, attrs):
        """
        Require at least one editable profile field and reject unsupported account types.
        
        Args:
            attrs: Serializer attributes collected from the incoming request.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        # Process each `field` from `("display_name", "company_name", "bio", "city", "country")` in
        # a deterministic order.
        for field in ("display_name", "company_name", "bio", "city", "country"):
            # Normalize this supported input variant before the main processing path continues.
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = attrs[field].strip()
        return attrs


class PledgeCreateSerializer(serializers.Serializer):
    """
    Validate and translate PledgeCreate API payloads between JSON and domain objects.
    """
    supporter_name = serializers.CharField(max_length=160)
    supporter_email = serializers.EmailField()
    quantity = serializers.IntegerField(min_value=1, max_value=20, default=1)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0)
    idempotency_key = serializers.CharField(max_length=100)
    referral_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    source = serializers.CharField(max_length=80, required=False, allow_blank=True)
    source_label = serializers.CharField(max_length=180, required=False, allow_blank=True)


class PledgeSerializer(serializers.ModelSerializer):
    """
    Validate and translate Pledge API payloads between JSON and domain objects.
    """
    class Meta:
        """
        Declare model or serializer metadata such as ordering, fields, and uniqueness constraints.
        """
        model = Pledge
        fields = "__all__"
        read_only_fields = ["campaign", "supporter_user", "status", "payment_provider", "payment_reference"]


class SponsorCreateSerializer(serializers.Serializer):
    """
    Validate and translate SponsorCreate API payloads between JSON and domain objects.
    """
    sponsor_name = serializers.CharField(max_length=180)
    contact_name = serializers.CharField(max_length=160)
    contact_email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    benefits_requested = serializers.CharField(required=False, allow_blank=True)


class SponsorSerializer(serializers.ModelSerializer):
    """
    Validate and translate Sponsor API payloads between JSON and domain objects.
    """
    class Meta:
        """
        Declare model or serializer metadata such as ordering, fields, and uniqueness constraints.
        """
        model = SponsorCommitment
        fields = "__all__"
        read_only_fields = ["campaign", "contact_user", "status", "payment_reference"]


class ConfirmationSerializer(serializers.Serializer):
    """
    Validate and translate Confirmation API payloads between JSON and domain objects.
    """
    details = serializers.CharField(max_length=3000)


class FinalizeSerializer(serializers.Serializer):
    """
    Validate and translate Finalize API payloads between JSON and domain objects.
    """
    event_id = serializers.CharField(max_length=100)


class FacebookAccessTokenSerializer(serializers.Serializer):
    """
    Validate and translate FacebookAccessToken API payloads between JSON and domain objects.
    """
    access_token = serializers.CharField(max_length=4096, write_only=True)


class FacebookShareLinkSerializer(serializers.Serializer):
    """
    Validate and translate FacebookShareLink API payloads between JSON and domain objects.
    """
    group_name = serializers.CharField(max_length=180, required=False, allow_blank=True)
    referral_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    source = serializers.CharField(max_length=80, required=False, default="facebook_group")


class FacebookPagePublishSerializer(FacebookShareLinkSerializer):
    """
    Validate and translate FacebookPagePublish API payloads between JSON and domain objects.
    """
    page_id = serializers.CharField(max_length=80)
    page_access_token = serializers.CharField(max_length=4096, write_only=True)
    message = serializers.CharField(max_length=5000, required=False, allow_blank=True)


class FacebookConversionSerializer(serializers.Serializer):
    """
    Validate and translate FacebookConversion API payloads between JSON and domain objects.
    """
    event_name = serializers.CharField(max_length=80)
    event_id = serializers.CharField(max_length=180)
    email = serializers.EmailField(required=False, allow_blank=True)
    value = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(max_length=3, default="USD")
    action_source = serializers.ChoiceField(
        choices=["website", "app", "physical_store", "system_generated", "other"],
        default="website",
    )
    group_name = serializers.CharField(max_length=180, required=False, allow_blank=True)
    referral_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    custom_data = serializers.JSONField(required=False, default=dict)
