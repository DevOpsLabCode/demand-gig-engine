# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provides self-service role requests and administrator-only verification decisions.

"""Authenticated API endpoints for multiple roles and role verification."""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .role_models import (
    Role,
    RoleAuditEvent,
    RoleCode,
    RoleVerificationStatus,
    UserRole,
)
from .role_serializers import (
    RoleRequestSerializer,
    RoleSerializer,
    UserRoleSerializer,
)


def can_verify_roles(user) -> bool:
    """Return whether a user is trusted to review other users' role requests."""

    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return UserRole.objects.filter(
        user=user,
        role__code=RoleCode.ADMINISTRATOR,
        verification_status=RoleVerificationStatus.VERIFIED,
    ).exists()


def _role_config(user) -> dict:
    """Build the current user's assignments and an optional administrator queue."""

    can_verify = can_verify_roles(user)
    assignments = UserRole.objects.filter(user=user).select_related(
        "role", "user", "verified_by"
    )
    available_roles = Role.objects.filter(active=True).exclude(
        code=RoleCode.ADMINISTRATOR
    )
    review_queue = UserRole.objects.none()
    if can_verify:
        review_queue = UserRole.objects.filter(
            verification_status=RoleVerificationStatus.PENDING,
            role__requires_verification=True,
        ).exclude(user=user).select_related("role", "user", "verified_by")

    return {
        "roles": RoleSerializer(available_roles, many=True).data,
        "assignments": UserRoleSerializer(assignments, many=True).data,
        "can_verify_roles": can_verify,
        "review_queue": UserRoleSerializer(review_queue, many=True).data,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def role_collection(request):
    """List role state or create/update one safe self-service role request."""

    if request.method == "GET":
        return Response(_role_config(request.user))

    serializer = RoleRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    role = get_object_or_404(
        Role,
        code=serializer.validated_data["role_code"],
        active=True,
    )
    organization_name = serializer.validated_data.get("organization_name", "")
    profile_data = serializer.validated_data.get("profile_data", {})

    with transaction.atomic():
        assignment, created = UserRole.objects.select_for_update().get_or_create(
            user=request.user,
            role=role,
            defaults={
                "organization_name": organization_name,
                "profile_data": profile_data,
                "verification_status": (
                    RoleVerificationStatus.PENDING
                    if role.requires_verification
                    else RoleVerificationStatus.VERIFIED
                ),
            },
        )

        event_type = "role_requested"
        if not created:
            assignment.organization_name = organization_name
            assignment.profile_data = profile_data
            if assignment.verification_status == RoleVerificationStatus.REJECTED:
                assignment.verification_status = RoleVerificationStatus.PENDING
                assignment.verified_by = None
                assignment.verified_at = None
                event_type = "role_request_resubmitted"
            else:
                event_type = "role_request_updated"
            assignment.save()

        RoleAuditEvent.objects.create(
            assignment=assignment,
            actor=request.user,
            event_type=event_type,
            payload={
                "organization_name": organization_name,
                "verification_status": assignment.verification_status,
            },
        )

    return Response(
        UserRoleSerializer(assignment).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


def _review_assignment(request, assignment_id: int, decision: str) -> Response:
    """Apply one administrator decision while preventing self-verification."""

    if not can_verify_roles(request.user):
        return Response(
            {"detail": "Administrator role verification is required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    with transaction.atomic():
        assignment = get_object_or_404(
            UserRole.objects.select_for_update().select_related("role", "user"),
            pk=assignment_id,
        )
        if assignment.user_id == request.user.id:
            return Response(
                {"detail": "Users may not verify or reject their own roles."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if assignment.role.code == RoleCode.FAN:
            return Response(
                {"detail": "The fan role is assigned automatically."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.verification_status = decision
        assignment.verified_by = request.user
        assignment.verified_at = timezone.now()
        assignment.save(
            update_fields=[
                "verification_status",
                "verified_by",
                "verified_at",
                "updated_at",
            ]
        )
        RoleAuditEvent.objects.create(
            assignment=assignment,
            actor=request.user,
            event_type=(
                "role_verified"
                if decision == RoleVerificationStatus.VERIFIED
                else "role_rejected"
            ),
            payload={"verification_status": decision},
        )

    return Response(UserRoleSerializer(assignment).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_role(request, assignment_id: int):
    """Verify another user's professional role as a trusted administrator."""

    return _review_assignment(
        request,
        assignment_id,
        RoleVerificationStatus.VERIFIED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_role(request, assignment_id: int):
    """Reject another user's professional role as a trusted administrator."""

    return _review_assignment(
        request,
        assignment_id,
        RoleVerificationStatus.REJECTED,
    )
