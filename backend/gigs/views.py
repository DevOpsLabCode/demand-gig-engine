from html import escape
import json
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .facebook import (
    MetaAPIError,
    build_campaign_share_link,
    list_managed_pages,
    publish_campaign_to_page,
    send_conversion_event,
    verify_facebook_user,
)
from .models import (
    DemandCampaign,
    ExternalResourceLink,
    IntegrationSyncStatus,
    IntegrationWebhookEvent,
    IntegrationWebhookStatus,
    Pledge,
    PledgeStatus,
)
from .serializers import (
    CampaignSerializer,
    ConfirmationSerializer,
    FacebookAccessTokenSerializer,
    FacebookConversionSerializer,
    FacebookPagePublishSerializer,
    FacebookShareLinkSerializer,
    FinalizeSerializer,
    PledgeCreateSerializer,
    PledgeSerializer,
    SponsorCreateSerializer,
    SponsorSerializer,
)
from integrations.vibesmeet.exceptions import VibesMeetAuthError, VibesMeetValidationError
from integrations.vibesmeet.webhooks import parse_verified_webhook

from .services import (
    CampaignStateError,
    confirm_artist,
    confirm_venue,
    create_pledge,
    create_sponsorship,
    evaluate_threshold_locked,
    fail_and_refund_campaign,
    finalize_campaign,
    launch_campaign,
    log_event,
)


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = DemandCampaign.objects.all()
    serializer_class = CampaignSerializer
    lookup_field = "slug"

    @action(detail=True, methods=["post"])
    def launch(self, request, slug=None):
        campaign = self.get_object()
        try:
            campaign = launch_campaign(campaign.id)
            return Response(CampaignSerializer(campaign).data)
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"])
    def pledge(self, request, slug=None):
        campaign = self.get_object()
        serializer = PledgeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pledge, client_secret = create_pledge(campaign.id, serializer.validated_data)
            return Response(
                {"pledge": PledgeSerializer(pledge).data, "client_secret": client_secret},
                status=status.HTTP_201_CREATED,
            )
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"])
    def sponsor(self, request, slug=None):
        campaign = self.get_object()
        serializer = SponsorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sponsorship = create_sponsorship(campaign.id, serializer.validated_data)
            return Response(SponsorSerializer(sponsorship).data, status=status.HTTP_201_CREATED)
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"], url_path="confirm-artist")
    def confirm_artist_action(self, request, slug=None):
        serializer = ConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = confirm_artist(self.get_object().id, serializer.validated_data["details"])
            return Response(CampaignSerializer(campaign).data)
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"], url_path="confirm-venue")
    def confirm_venue_action(self, request, slug=None):
        serializer = ConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = confirm_venue(self.get_object().id, serializer.validated_data["details"])
            return Response(CampaignSerializer(campaign).data)
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"])
    def finalize(self, request, slug=None):
        serializer = FinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = finalize_campaign(self.get_object().id, serializer.validated_data["event_id"])
            return Response(CampaignSerializer(campaign).data)
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"])
    def refund(self, request, slug=None):
        try:
            campaign = fail_and_refund_campaign(self.get_object().id, request.data.get("reason", "Canceled"))
            return Response(CampaignSerializer(campaign).data)
        except CampaignStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"], url_path="facebook/share-link")
    def facebook_share_link(self, request, slug=None):
        serializer = FacebookShareLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = self.get_object()
        link = build_campaign_share_link(
            campaign.slug,
            source=serializer.validated_data.get("source", "facebook_group"),
            group_name=serializer.validated_data.get("group_name", ""),
            referral_code=serializer.validated_data.get("referral_code", ""),
        )
        log_event(
            campaign,
            "facebook.share_link_created",
            source=serializer.validated_data.get("source", "facebook_group"),
            group_name=serializer.validated_data.get("group_name", ""),
            referral_code=serializer.validated_data.get("referral_code", ""),
        )
        return Response({"campaign_url": link.campaign_url, "share_dialog_url": link.share_dialog_url})

    @action(detail=True, methods=["post"], url_path="facebook/track-conversion")
    def facebook_track_conversion(self, request, slug=None):
        serializer = FacebookConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = self.get_object()
        link = build_campaign_share_link(
            campaign.slug,
            source="facebook_conversion",
            group_name=serializer.validated_data.get("group_name", ""),
            referral_code=serializer.validated_data.get("referral_code", ""),
        )
        custom_data = {
            "content_name": campaign.title,
            "content_category": "demand_driven_gig",
            "campaign_slug": campaign.slug,
            **serializer.validated_data.get("custom_data", {}),
        }
        try:
            result = send_conversion_event(
                event_name=serializer.validated_data["event_name"],
                event_id=serializer.validated_data["event_id"],
                event_source_url=link.campaign_url,
                email=serializer.validated_data.get("email", ""),
                value=serializer.validated_data.get("value"),
                currency=serializer.validated_data.get("currency", campaign.currency),
                custom_data=custom_data,
                action_source=serializer.validated_data.get("action_source", "website"),
            )
        except MetaAPIError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        log_event(
            campaign,
            "facebook.conversion_forwarded",
            event_name=serializer.validated_data["event_name"],
            event_id=serializer.validated_data["event_id"],
            action_source=serializer.validated_data.get("action_source", "website"),
            configured=result is not None,
        )
        return Response({"forwarded": result is not None, "meta_response": result or {}})

    @action(detail=True, methods=["post"], url_path="facebook/publish-page")
    def facebook_publish_page(self, request, slug=None):
        serializer = FacebookPagePublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = self.get_object()
        link = build_campaign_share_link(
            campaign.slug,
            source=serializer.validated_data.get("source", "facebook_page"),
            group_name=serializer.validated_data.get("group_name", ""),
            referral_code=serializer.validated_data.get("referral_code", ""),
        )
        message = serializer.validated_data.get("message") or (
            f"{campaign.title}\n\n{campaign.pitch}\n\n"
            "Support the seed. The gig is confirmed only when enough fans commit."
        )
        try:
            result = publish_campaign_to_page(
                page_id=serializer.validated_data["page_id"],
                page_access_token=serializer.validated_data["page_access_token"],
                message=message,
                link=link.campaign_url,
            )
        except MetaAPIError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        log_event(
            campaign,
            "facebook.page_post_published",
            page_id=serializer.validated_data["page_id"],
            post_id=result.get("id", ""),
        )
        return Response({"post_id": result.get("id", ""), "campaign_url": link.campaign_url})


@api_view(["GET"])
def facebook_config(request):
    return Response(
        {
            "enabled": bool(settings.META_APP_ID and settings.META_APP_SECRET),
            "app_id": settings.META_APP_ID,
            "pixel_id": settings.META_PIXEL_ID,
            "graph_api_version": settings.META_GRAPH_API_VERSION,
            "groups_api_available": False,
        }
    )


@api_view(["POST"])
def facebook_login(request):
    serializer = FacebookAccessTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        profile = verify_facebook_user(serializer.validated_data["access_token"])
    except MetaAPIError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(profile)


@api_view(["POST"])
def facebook_pages(request):
    serializer = FacebookAccessTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        pages = list_managed_pages(serializer.validated_data["access_token"])
    except MetaAPIError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(pages)


def campaign_share_page(request, slug: str):
    campaign = DemandCampaign.objects.filter(slug=slug).first()
    if not campaign:
        return HttpResponse("Campaign not found", status=404)

    source = request.GET.get("source", "facebook_group")[:80]
    group_name = request.GET.get("group", "")[:180]
    referral_code = request.GET.get("ref", "")[:80]
    frontend_query = urlencode(
        {
            "campaign": campaign.slug,
            "source": source,
            "group": group_name,
            "ref": referral_code,
        }
    )
    destination = f"{settings.FRONTEND_URL.rstrip('/')}/?{frontend_query}"
    canonical = build_campaign_share_link(
        campaign.slug,
        source=source,
        group_name=group_name,
        referral_code=referral_code,
    ).campaign_url
    progress = campaign.progress_percent
    description = (
        f"{campaign.active_supporter_count:,} of {campaign.supporter_target:,} supporters and "
        f"{campaign.currency} {campaign.committed_amount:,.2f} committed. {campaign.pitch}"
    )[:300]
    image_meta = (
        f'<meta property="og:image" content="{escape(settings.META_DEFAULT_SHARE_IMAGE)}">'
        if settings.META_DEFAULT_SHARE_IMAGE
        else ""
    )
    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(campaign.title)}</title>
<meta name="description" content="{escape(description)}">
<link rel="canonical" href="{escape(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{escape(campaign.title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{escape(canonical)}">
<meta property="og:site_name" content="Open Concert × VibesMeet">
{image_meta}
<meta name="twitter:card" content="summary_large_image">
<style>
body{{font-family:Inter,system-ui,sans-serif;background:#09090d;color:#fff;margin:0;display:grid;place-items:center;min-height:100vh}}
main{{max-width:720px;padding:42px;border:1px solid #302e37;border-radius:24px;background:#111017;margin:24px}}
small{{color:#b991ff;text-transform:uppercase;letter-spacing:.12em;font-weight:800}}
h1{{font-size:clamp(38px,7vw,66px);line-height:1;margin:16px 0}}p{{color:#bbb8c3;line-height:1.6}}
.track{{height:12px;background:#292631;border-radius:20px;overflow:hidden;margin:26px 0}}.track span{{display:block;height:100%;width:{progress}%;background:linear-gradient(90deg,#8b5cf6,#35cba6)}}
a{{display:inline-block;color:white;background:#7c3aed;padding:14px 20px;border-radius:12px;text-decoration:none;font-weight:800}}
</style></head><body><main>
<small>Demand-driven gig seed</small><h1>{escape(campaign.title)}</h1>
<p>{escape(campaign.pitch)}</p><div class="track"><span></span></div>
<p><strong>{campaign.active_supporter_count:,}</strong> supporters · <strong>{campaign.currency} {campaign.committed_amount:,.2f}</strong> committed · {progress}% minimum demand</p>
<a href="{escape(destination)}">Make this gig happen</a>
</main></body></html>"""
    return HttpResponse(html)


@api_view(["POST"])
def stripe_webhook(request):
    """Updates a pledge after Stripe confirms or rejects the PaymentIntent."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        return Response({"detail": "Stripe webhook is not configured."}, status=503)

    import stripe
    try:
        event = stripe.Webhook.construct_event(
            payload=request.body,
            sig_header=request.headers.get("Stripe-Signature", ""),
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return Response({"detail": "Invalid webhook."}, status=400)

    obj = event["data"]["object"]
    if event["type"] in ["payment_intent.succeeded", "payment_intent.payment_failed"]:
        with transaction.atomic():
            pledge = Pledge.objects.select_for_update().filter(payment_reference=obj["id"]).first()
            if pledge:
                if event["type"] == "payment_intent.succeeded" and pledge.status == PledgeStatus.PENDING:
                    pledge.status = PledgeStatus.PAID
                    pledge.save(update_fields=["status", "updated_at"])
                    campaign = DemandCampaign.objects.select_for_update().get(pk=pledge.campaign_id)
                    evaluate_threshold_locked(campaign)
                elif event["type"] == "payment_intent.payment_failed" and pledge.status == PledgeStatus.PENDING:
                    pledge.status = PledgeStatus.FAILED
                    pledge.save(update_fields=["status", "updated_at"])
    return HttpResponse(status=200)


@api_view(["GET"])
def vibesmeet_config(request):
    """Expose non-secret integration readiness for the organizer UI."""
    return Response(
        {
            "enabled": bool(settings.VIBESMEET_BASE_URL and settings.VIBESMEET_ACCESS_TOKEN),
            "webhook_configured": bool(settings.VIBESMEET_WEBHOOK_SECRET),
            "base_url": settings.VIBESMEET_BASE_URL,
            "contract_status": "proposed_pending_vibesmeet_confirmation",
            "supports": {
                "outbound_client": True,
                "signed_webhook_inbox": True,
                "external_resource_mapping": True,
                "reservation_conversion": "contract_defined_not_wired",
            },
        }
    )


@api_view(["POST"])
@transaction.atomic
def vibesmeet_webhook(request):
    """Verify and persist one proposed VibesMeet partner webhook event.

    Processing is deliberately conservative: known events are recorded and
    linked to a campaign, while unknown events are quarantined for review.
    Business-state transitions should be added only after the VibesMeet event
    contract is finalized.
    """
    if not settings.VIBESMEET_WEBHOOK_SECRET:
        return Response({"detail": "VibesMeet webhook is not configured."}, status=503)

    timestamp = request.headers.get("X-VibesMeet-Timestamp", "")
    signature = request.headers.get("X-VibesMeet-Signature", "")
    try:
        envelope = parse_verified_webhook(
            raw_body=request.body,
            timestamp=timestamp,
            signature=signature,
            secret=settings.VIBESMEET_WEBHOOK_SECRET,
            tolerance_seconds=settings.VIBESMEET_WEBHOOK_TOLERANCE_SECONDS,
        )
    except VibesMeetAuthError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
    except VibesMeetValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        raw_payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raw_payload = {}

    webhook, created = IntegrationWebhookEvent.objects.get_or_create(
        provider="vibesmeet",
        event_id=envelope.event_id,
        defaults={
            "event_type": envelope.event_type,
            "resource_type": envelope.resource_type,
            "resource_id": envelope.resource_id,
            "resource_version": envelope.resource_version,
            "sequence": envelope.sequence,
            "payload": raw_payload,
        },
    )
    if not created:
        return Response(
            {
                "accepted": True,
                "duplicate": True,
                "event_id": webhook.event_id,
                "status": webhook.status,
            }
        )

    campaign = None
    campaign_id = str(envelope.partner_reference.get("campaign_id") or "")
    if campaign_id:
        try:
            campaign = DemandCampaign.objects.filter(pk=campaign_id).first()
        except (TypeError, ValueError, DjangoValidationError):
            campaign = None

    if campaign is not None:
        log_event(
            campaign,
            "vibesmeet.webhook.received",
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            resource_type=envelope.resource_type,
            resource_id=envelope.resource_id,
            resource_version=envelope.resource_version,
            sequence=envelope.sequence,
        )
        if envelope.resource_type and envelope.resource_id:
            try:
                # Use a savepoint so a mapping conflict does not poison the
                # outer webhook transaction.
                with transaction.atomic():
                    ExternalResourceLink.objects.update_or_create(
                        provider="vibesmeet",
                        local_resource_type="demand_campaign",
                        local_resource_id=str(campaign.id),
                        remote_resource_type=envelope.resource_type,
                        defaults={
                            "remote_resource_id": envelope.resource_id,
                            "remote_version": envelope.resource_version,
                            "sync_status": IntegrationSyncStatus.SYNCED,
                            "last_synced_at": timezone.now(),
                        },
                    )
            except IntegrityError:
                webhook.status = IntegrationWebhookStatus.QUARANTINED
                webhook.error = "Remote resource is already mapped to another local record."

    if webhook.status != IntegrationWebhookStatus.QUARANTINED:
        webhook.status = (
            IntegrationWebhookStatus.QUARANTINED
            if envelope.event_type.startswith("unknown:")
            else IntegrationWebhookStatus.PROCESSED
        )
    webhook.processed_at = timezone.now()
    webhook.save(update_fields=["status", "error", "processed_at"])

    return Response(
        {
            "accepted": True,
            "duplicate": False,
            "event_id": webhook.event_id,
            "status": webhook.status,
            "campaign_mapped": campaign is not None,
        }
    )
