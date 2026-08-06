# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Validates date options, ticket-price options, and private supporter preference input.

"""Phase 2 serializers."""

from rest_framework import serializers

from .campaign_preference_models import (
    CampaignDateOption,
    CampaignPriceOption,
    SupporterPreference,
)


class CampaignDateOptionSerializer(serializers.ModelSerializer):
    """Validate one proposed date without exposing campaign ownership internals."""

    class Meta:
        model = CampaignDateOption
        fields = [
            "id",
            "start_datetime",
            "end_datetime",
            "venue_timezone",
            "label",
            "active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        start = attrs.get(
            "start_datetime",
            getattr(self.instance, "start_datetime", None),
        )
        end = attrs.get("end_datetime", getattr(self.instance, "end_datetime", None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_datetime": "End time must be later than the start time."}
            )
        return attrs


class CampaignPriceOptionSerializer(serializers.ModelSerializer):
    """Validate one acceptable ticket-price choice."""

    class Meta:
        model = CampaignPriceOption
        fields = ["id", "amount", "currency", "label", "active"]
        read_only_fields = ["id"]

    def validate_currency(self, value):
        return value.upper()


class SupporterPreferenceSerializer(serializers.ModelSerializer):
    """Validate the current user's private preference for one campaign."""

    class Meta:
        model = SupporterPreference
        fields = [
            "id",
            "expected_quantity",
            "attendance_mode",
            "selected_date_option",
            "selected_price_option",
            "preferred_neighborhood",
            "accessibility_notes",
            "referral_source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "expected_quantity": {"min_value": 1, "max_value": 20},
        }

    def validate(self, attrs):
        campaign = self.context["campaign"]
        date_option = attrs.get(
            "selected_date_option",
            getattr(self.instance, "selected_date_option", None),
        )
        price_option = attrs.get(
            "selected_price_option",
            getattr(self.instance, "selected_price_option", None),
        )

        if date_option is None:
            raise serializers.ValidationError(
                {"selected_date_option": "Select one proposed date."}
            )
        if price_option is None:
            raise serializers.ValidationError(
                {"selected_price_option": "Select one acceptable ticket price."}
            )
        if date_option.campaign_id != campaign.id or not date_option.active:
            raise serializers.ValidationError(
                {"selected_date_option": "Select an active date from this campaign."}
            )
        if price_option.campaign_id != campaign.id or not price_option.active:
            raise serializers.ValidationError(
                {"selected_price_option": "Select an active price from this campaign."}
            )

        for field in (
            "preferred_neighborhood",
            "accessibility_notes",
            "referral_source",
        ):
            if field in attrs:
                attrs[field] = attrs[field].strip()
        return attrs
