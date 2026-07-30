from django.utils import timezone
from rest_framework import serializers
from .models import DemandCampaign, Pledge, SponsorCommitment


class CampaignSerializer(serializers.ModelSerializer):
    active_supporter_count = serializers.IntegerField(read_only=True)
    committed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    target_reached = serializers.BooleanField(read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = DemandCampaign
        fields = [
            "id", "title", "slug", "pitch", "artist_name", "city", "country", "proposed_date",
            "deadline", "goal_type", "supporter_target", "amount_target", "suggested_deposit",
            "currency", "status", "artist_confirmed", "venue_confirmed", "confirmed_artist_details",
            "confirmed_venue_details", "event_id", "organizer_name", "organizer_email",
            "facebook_event_url", "facebook_group_url", "facebook_page_url",
            "active_supporter_count", "committed_amount", "target_reached", "progress_percent",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "slug", "status", "artist_confirmed", "venue_confirmed", "confirmed_artist_details",
            "confirmed_venue_details", "event_id", "created_at", "updated_at",
        ]

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Deadline must be in the future.")
        return value

    def validate(self, attrs):
        goal_type = attrs.get("goal_type", getattr(self.instance, "goal_type", "supporters"))
        supporter_target = attrs.get("supporter_target", getattr(self.instance, "supporter_target", 0))
        amount_target = attrs.get("amount_target", getattr(self.instance, "amount_target", 0))
        if goal_type in ("supporters", "both") and supporter_target < 1:
            raise serializers.ValidationError({"supporter_target": "Must be at least 1 for this goal type."})
        if goal_type in ("money", "both") and amount_target <= 0:
            raise serializers.ValidationError({"amount_target": "Must be greater than zero for this goal type."})
        if "currency" in attrs:
            attrs["currency"] = attrs["currency"].upper()
        return attrs


class PledgeCreateSerializer(serializers.Serializer):
    supporter_name = serializers.CharField(max_length=160)
    supporter_email = serializers.EmailField()
    quantity = serializers.IntegerField(min_value=1, max_value=20, default=1)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0)
    idempotency_key = serializers.CharField(max_length=100)
    referral_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    source = serializers.CharField(max_length=80, required=False, allow_blank=True)
    source_label = serializers.CharField(max_length=180, required=False, allow_blank=True)


class PledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pledge
        fields = "__all__"
        read_only_fields = ["campaign", "status", "payment_provider", "payment_reference"]


class SponsorCreateSerializer(serializers.Serializer):
    sponsor_name = serializers.CharField(max_length=180)
    contact_name = serializers.CharField(max_length=160)
    contact_email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    benefits_requested = serializers.CharField(required=False, allow_blank=True)


class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsorCommitment
        fields = "__all__"
        read_only_fields = ["campaign", "status", "payment_reference"]


class ConfirmationSerializer(serializers.Serializer):
    details = serializers.CharField(max_length=3000)


class FinalizeSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=100)


class FacebookAccessTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField(max_length=4096, write_only=True)


class FacebookShareLinkSerializer(serializers.Serializer):
    group_name = serializers.CharField(max_length=180, required=False, allow_blank=True)
    referral_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    source = serializers.CharField(max_length=80, required=False, default="facebook_group")


class FacebookPagePublishSerializer(FacebookShareLinkSerializer):
    page_id = serializers.CharField(max_length=80)
    page_access_token = serializers.CharField(max_length=4096, write_only=True)
    message = serializers.CharField(max_length=5000, required=False, allow_blank=True)


class FacebookConversionSerializer(serializers.Serializer):
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
