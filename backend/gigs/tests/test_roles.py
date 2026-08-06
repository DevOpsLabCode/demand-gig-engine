# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies multiple-role requests, safe legacy compatibility, administrator decisions, and role audit events.

from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from gigs.models import AccountType
from gigs.role_models import (
    Role,
    RoleAuditEvent,
    RoleCode,
    RoleVerificationStatus,
    UserRole,
)


@pytest.fixture
def user_factory(db):
    def create(username: str, *, staff: bool = False):
        return get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="OpenConcert!2026-Ready",
            is_staff=staff,
        )

    return create


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_registration_assigns_verified_fan_role():
    client = APIClient()
    response = client.post(
        "/api/auth/register/",
        {
            "display_name": "Role Member",
            "email": "roles@example.com",
            "password": "OpenConcert!2026-Ready",
            "password_confirm": "OpenConcert!2026-Ready",
        },
        format="json",
    )

    assert response.status_code == 201
    user = get_user_model().objects.get(email="roles@example.com")
    assignment = UserRole.objects.get(user=user, role__code=RoleCode.FAN)
    assert assignment.verification_status == RoleVerificationStatus.VERIFIED
    assert assignment.audit_events.filter(event_type="role_assigned").exists()


@pytest.mark.django_db
def test_user_requests_multiple_professional_roles(user_factory):
    user = user_factory("multi-role")
    client = authenticated_client(user)

    organizer = client.post(
        "/api/auth/roles/",
        {
            "role_code": "organizer",
            "organization_name": "Open Concert",
            "profile_data": {"experience_years": 10},
        },
        format="json",
    )
    vendor = client.post(
        "/api/auth/roles/",
        {
            "role_code": "vendor",
            "organization_name": "Stage Services",
        },
        format="json",
    )

    assert organizer.status_code == 201
    assert vendor.status_code == 201
    assert organizer.data["verification_status"] == "pending"
    assert UserRole.objects.filter(user=user).count() == 3
    assert set(
        UserRole.objects.filter(user=user).values_list("role__code", flat=True)
    ) == {"fan", "organizer", "vendor"}


@pytest.mark.django_db
def test_user_cannot_request_administrator_or_send_non_object_profile_data(user_factory):
    client = authenticated_client(user_factory("restricted-role"))

    administrator = client.post(
        "/api/auth/roles/",
        {"role_code": "administrator"},
        format="json",
    )
    malformed = client.post(
        "/api/auth/roles/",
        {"role_code": "artist", "profile_data": ["not", "an", "object"]},
        format="json",
    )

    assert administrator.status_code == 400
    assert malformed.status_code == 400


@pytest.mark.django_db
def test_rejected_role_can_be_resubmitted_and_metadata_updated(user_factory):
    user = user_factory("resubmit-role")
    role = Role.objects.get(code=RoleCode.VENUE)
    assignment = UserRole.objects.create(
        user=user,
        role=role,
        verification_status=RoleVerificationStatus.REJECTED,
    )
    client = authenticated_client(user)

    response = client.post(
        "/api/auth/roles/",
        {
            "role_code": "venue",
            "organization_name": "Village Hall",
            "profile_data": {"capacity": 350},
        },
        format="json",
    )

    assert response.status_code == 200
    assignment.refresh_from_db()
    assert assignment.verification_status == RoleVerificationStatus.PENDING
    assert assignment.organization_name == "Village Hall"
    assert assignment.audit_events.filter(
        event_type="role_request_resubmitted"
    ).exists()


@pytest.mark.django_db
def test_staff_verifies_and_rejects_other_users_roles(user_factory):
    reviewer = user_factory("staff-reviewer", staff=True)
    target = user_factory("review-target")
    organizer = UserRole.objects.create(
        user=target,
        role=Role.objects.get(code=RoleCode.ORGANIZER),
    )
    vendor = UserRole.objects.create(
        user=target,
        role=Role.objects.get(code=RoleCode.VENDOR),
    )
    client = authenticated_client(reviewer)

    verified = client.post(f"/api/auth/roles/{organizer.id}/verify/", {}, format="json")
    rejected = client.post(f"/api/auth/roles/{vendor.id}/reject/", {}, format="json")

    assert verified.status_code == 200
    assert rejected.status_code == 200
    organizer.refresh_from_db()
    vendor.refresh_from_db()
    assert organizer.verification_status == RoleVerificationStatus.VERIFIED
    assert vendor.verification_status == RoleVerificationStatus.REJECTED
    assert organizer.verified_by == reviewer
    assert organizer.verified_at is not None
    assert RoleAuditEvent.objects.filter(
        assignment=organizer,
        event_type="role_verified",
        actor=reviewer,
    ).exists()


@pytest.mark.django_db
def test_staff_user_cannot_verify_own_role(user_factory):
    reviewer = user_factory("self-reviewer", staff=True)
    assignment = UserRole.objects.create(
        user=reviewer,
        role=Role.objects.get(code=RoleCode.ORGANIZER),
    )

    response = authenticated_client(reviewer).post(
        f"/api/auth/roles/{assignment.id}/verify/",
        {},
        format="json",
    )

    assert response.status_code == 403
    assignment.refresh_from_db()
    assert assignment.verification_status == RoleVerificationStatus.PENDING


@pytest.mark.django_db
def test_verified_administrator_role_can_review_others(user_factory):
    reviewer = user_factory("role-admin")
    target = user_factory("role-admin-target")
    UserRole.objects.create(
        user=reviewer,
        role=Role.objects.get(code=RoleCode.ADMINISTRATOR),
        verification_status=RoleVerificationStatus.VERIFIED,
    )
    assignment = UserRole.objects.create(
        user=target,
        role=Role.objects.get(code=RoleCode.ARTIST),
    )

    response = authenticated_client(reviewer).post(
        f"/api/auth/roles/{assignment.id}/verify/",
        {},
        format="json",
    )

    assert response.status_code == 200
    assignment.refresh_from_db()
    assert assignment.verification_status == RoleVerificationStatus.VERIFIED


@pytest.mark.django_db
def test_role_config_hides_administrator_and_limits_review_queue(user_factory):
    ordinary = user_factory("ordinary")
    reviewer = user_factory("queue-reviewer", staff=True)
    target = user_factory("queue-target")
    pending = UserRole.objects.create(
        user=target,
        role=Role.objects.get(code=RoleCode.SPONSOR),
    )

    ordinary_response = authenticated_client(ordinary).get("/api/auth/roles/")
    reviewer_response = authenticated_client(reviewer).get("/api/auth/roles/")

    assert ordinary_response.status_code == 200
    assert ordinary_response.data["can_verify_roles"] is False
    assert ordinary_response.data["review_queue"] == []
    assert "administrator" not in {
        role["code"] for role in ordinary_response.data["roles"]
    }
    assert reviewer_response.data["can_verify_roles"] is True
    assert pending.id in {
        item["id"] for item in reviewer_response.data["review_queue"]
    }


@pytest.mark.django_db
def test_legacy_account_type_update_adds_role_without_removing_fan(user_factory):
    user = user_factory("legacy-update")
    response = authenticated_client(user).patch(
        "/api/auth/profile/",
        {
            "account_type": AccountType.RENTAL,
            "company_name": "Rental Company",
        },
        format="json",
    )

    assert response.status_code == 200
    assert set(
        UserRole.objects.filter(user=user).values_list("role__code", flat=True)
    ) == {RoleCode.FAN, RoleCode.EQUIPMENT_RENTAL}
    rental = UserRole.objects.get(user=user, role__code=RoleCode.EQUIPMENT_RENTAL)
    assert rental.verification_status == RoleVerificationStatus.PENDING


@pytest.mark.django_db
def test_backfill_function_is_idempotent_and_maps_legacy_values(user_factory):
    user = user_factory("legacy-migration")
    profile = user.gig_profile
    profile.account_type = AccountType.BAND
    profile.company_name = "Legacy Band"
    profile.verified = True
    profile.save()
    UserRole.objects.filter(user=user).delete()

    migration = import_module("gigs.migrations.0006_multiple_roles")
    migration.seed_roles_and_backfill(apps, None)
    migration.seed_roles_and_backfill(apps, None)

    assignments = UserRole.objects.filter(user=user)
    assert assignments.count() == 2
    assert assignments.get(role__code=RoleCode.FAN).is_verified
    artist = assignments.get(role__code=RoleCode.ARTIST)
    assert artist.is_verified
    assert artist.organization_name == "Legacy Band"
