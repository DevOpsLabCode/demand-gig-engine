# Code Walkthrough - Demand Gig Engine

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

This guide explains where behavior lives and how the major code blocks cooperate. The source files also contain inline comments and docstrings, so this document is an index rather than a substitute for reading the code.

## How to follow one campaign

1. React components call typed functions in `frontend/src/api.ts`.
2. Django routes in `backend/gigs/urls.py` dispatch to `backend/gigs/views.py`.
3. Serializers validate untrusted JSON before a service function is called.
4. `backend/gigs/services.py` performs the state transition inside database transactions.
5. `backend/gigs/models.py` enforces persistence, uniqueness, and status semantics.
6. Payment, Facebook/Meta, and VibesMeet adapters isolate external network behavior.
7. Terraform modules create the AWS services required to run the same flow in production.

## Reading conventions

- **Module header:** states the file purpose and author.
- **Docstring/JSDoc:** explains a class, function, component, test, or contract.
- **Inline control-flow comment:** explains why an `if`, loop, transaction, retry, or exception block exists.
- **Terraform block comment:** explains the operational responsibility of a resource, data source, module, variable, or output.

## GitHub automation

### `.github/dependabot.yml`

Schedules weekly dependency update pull requests for Python, npm, GitHub Actions, and Docker while applying security-focused labels and limits.

### `.github/workflows/codeql.yml`

Runs CodeQL analysis for Python and JavaScript/TypeScript on pushes, pull requests, a weekly schedule, and manual requests.

### `.github/workflows/dependency-review.yml`

Reviews dependency changes in pull requests and blocks newly introduced packages that violate the configured vulnerability policy.

### `.github/workflows/python-package.yml`

Validates the Django backend and React frontend with dependency installation, linting, tests, coverage enforcement, and a production build.

### `.github/workflows/security.yml`

Runs scheduled and pull-request security gates across Python, npm, source code, secrets, containers, and infrastructure configuration.

### `.github/workflows/terraform.yml`

Validates infrastructure with Terraform formatting and native validation, TFLint, Checkov, Go contract tests, and shell-script checks.

## Backend and Python tooling

### `backend/config/__init__.py`

Marks the Django project configuration directory as an importable Python package.

### `backend/config/settings.py`

Centralizes Django, database, cache, security, social-authentication, storage, tracing, and third-party runtime configuration.

- Function `_social_app()` - Build one django-allauth provider configuration from environment-supplied client credentials.
- Function `env_bool()` - Parse a boolean environment variable while honoring a safe default when it is unset.

### `backend/config/urls.py`

Defines the project-level URL router that connects administration, authentication, health, API, and integration endpoints.

### `backend/config/wsgi.py`

Exposes the WSGI application used by Gunicorn and other production-compatible Python web servers.

### `backend/gigs/__init__.py`

Marks the gigs domain as a Python package so Django can import its models, services, views, signals, and management commands.

### `backend/gigs/admin.py`

Registers domain models with Django Admin and selects useful list, search, and filtering fields.

- Class `DemandCampaignAdmin` - Configure Django Admin list, search, filtering, and display behavior for DemandCampaign records.
- Class `PledgeAdmin` - Configure Django Admin list, search, filtering, and display behavior for Pledge records.
- Class `SponsorCommitmentAdmin` - Configure Django Admin list, search, filtering, and display behavior for SponsorCommitment records.
- Class `CampaignEventAdmin` - Configure Django Admin list, search, filtering, and display behavior for CampaignEvent records.
- Class `ExternalResourceLinkAdmin` - Configure Django Admin list, search, filtering, and display behavior for ExternalResourceLink records.
- Class `IntegrationWebhookEventAdmin` - Configure Django Admin list, search, filtering, and display behavior for IntegrationWebhookEvent records.
- Class `GigUserProfileAdmin` - Configure Django Admin list, search, filtering, and display behavior for GigUserProfile records.

### `backend/gigs/apps.py`

Declares the Django application and loads signal handlers when the application registry is ready.

- Class `GigsConfig` - Register the gigs Django application and load signal handlers only after the application registry is ready.
-   - `GigsConfig.ready()` - Import signal handlers after Django finishes loading the application registry.

### `backend/gigs/auth_views.py`

Returns frontend authentication configuration, authenticated profile data, logout behavior, and health status.

- Function `_serialize_user()` - Convert the authenticated Django user and linked social identities into the frontend profile contract.
- Function `auth_config()` - Return enabled social-login providers, the current user profile, and a CSRF token for the browser.
- Function `auth_profile()` - Validate and persist the authenticated user's editable organizer profile fields.
- Function `auth_logout()` - End the current Django session and return an empty success response.
- Function `health()` - Provide a dependency-light liveness endpoint for containers and the load balancer.

### `backend/gigs/facebook.py`

Builds tracked Facebook share links and integrates supported Meta Graph and Conversions API operations.

- Class `MetaAPIError` - Represent a controlled Meta Graph or Conversions API failure.
- Class `FacebookShareLink` - Carry the tracked campaign URL and the final Facebook share-dialog URL.
- Function `_graph_url()` - Join the configured Meta Graph API version and endpoint without producing duplicate slashes.
- Function `_request_json()` - Call the Meta Graph API and translate transport or API payload failures into MetaAPIError.
- Function `build_campaign_share_link()` - Build a campaign URL and Facebook share URL carrying source, group, and referral attribution.
- Function `verify_facebook_user()` - Validate a user access token against the configured Meta app and return a normalized profile.
- Function `list_managed_pages()` - Return Facebook Pages the authenticated organizer is allowed to manage.
- Function `publish_campaign_to_page()` - Publish the tracked campaign message to a selected managed Facebook Page.
- Function `_sha256()` - Normalize a value and return the SHA-256 digest required by Meta advanced matching.
- Function `send_conversion_event()` - Send a deduplicated browser/server-compatible event to the Meta Conversions API when configured.

### `backend/gigs/management/__init__.py`

Marks Django management tooling for the gigs application as an importable package.

### `backend/gigs/management/commands/__init__.py`

Marks the custom Django management-command directory so commands are discovered by manage.py.

### `backend/gigs/management/commands/expire_campaigns.py`

Provides a one-shot Django command that fails overdue campaigns which missed their threshold and triggers refundable-deposit processing.

- Class `Command` - Expose overdue-campaign expiry and refundable-deposit processing as a one-shot Django management command.
-   - `Command.handle()` - Expire overdue campaigns that missed their threshold and report how many were processed.

### `backend/gigs/management/commands/process_tasks.py`

Process asynchronous Demand Gig Engine jobs from Amazon SQS.

- Class `Command` - Run the long-polling SQS worker with bounded waits, graceful shutdown, acknowledgement, and retry-preserving failure behavior.
-   - `Command.add_arguments()` - Register command-line switches that control worker polling and one-shot execution.
-   - `Command.handle()` - Poll SQS for campaign-expiry jobs, process them safely, and acknowledge only completed work.
-   - `Command._process_message()` - Validate one SQS job, dispatch supported work, and acknowledge only successfully handled messages.

### `backend/gigs/management/commands/seed_demo.py`

Creates and launches an idempotent sample campaign so developers can evaluate the complete demand-validation flow locally.

- Class `Command` - Create the canonical local demonstration campaign once and launch it without duplicating data on repeated runs.
-   - `Command.handle()` - Create an idempotent demonstration campaign and sample support records for local evaluation.

### `backend/gigs/migrations/0001_initial.py`

Records the database schema transition represented by migration 0001_initial.

- Class `Migration` - Describe the database schema transition and its dependency on earlier migrations.

### `backend/gigs/migrations/0002_facebook_hub_urls.py`

Records the database schema transition represented by migration 0002_facebook_hub_urls.

- Class `Migration` - Describe the database schema transition and its dependency on earlier migrations.

### `backend/gigs/migrations/0003_scope_pledge_idempotency.py`

Records the database schema transition represented by migration 0003_scope_pledge_idempotency.

- Class `Migration` - Describe the database schema transition and its dependency on earlier migrations.

### `backend/gigs/migrations/0004_vibesmeet_integration_foundation.py`

Records the database schema transition represented by migration 0004_vibesmeet_integration_foundation.

- Class `Migration` - Describe the database schema transition and its dependency on earlier migrations.

### `backend/gigs/migrations/0005_social_auth_and_ownership.py`

Records the database schema transition represented by migration 0005_social_auth_and_ownership.

- Class `Migration` - Describe the database schema transition and its dependency on earlier migrations.

### `backend/gigs/migrations/__init__.py`

Records the database schema transition represented by migration __init__.

### `backend/gigs/models.py`

Defines the persistent domain model for accounts, demand campaigns, pledges, sponsors, events, and integration audit records.

- Class `AccountType` - Enumerate the stable database/API values for AccountType.
- Class `GigUserProfile` - Persist GigUserProfile state and enforce its domain-level invariants.
-   - `GigUserProfile.__str__()` - Return a readable user/profile label for Django Admin, logs, and debugging.
- Class `CampaignStatus` - Enumerate the stable database/API values for CampaignStatus.
- Class `GoalType` - Enumerate the stable database/API values for GoalType.
- Class `DemandCampaign` - Persist DemandCampaign state and enforce its domain-level invariants.
-   - `DemandCampaign.clean()` - Validate cross-field campaign rules such as positive targets and future deadlines.
-   - `DemandCampaign.save()` - Generate a unique slug when needed, then persist the campaign normally.
-   - `DemandCampaign.active_supporter_count()` - Count ticket quantities from pledges that still contribute to the campaign.
-   - `DemandCampaign.committed_amount()` - Sum active supporter deposits and sponsor commitments in the campaign currency.
-   - `DemandCampaign.target_reached()` - Evaluate the configured supporter-count or monetary threshold.
-   - `DemandCampaign.progress_percent()` - Return threshold progress as a percentage capped at 100 for display.
-   - `DemandCampaign.__str__()` - Return the campaign title as its human-readable model representation.
- Class `PledgeStatus` - Enumerate the stable database/API values for PledgeStatus.
- Class `Pledge` - Persist Pledge state and enforce its domain-level invariants.
-   - `Pledge.active_statuses()` - Return pledge states that still count toward demand and committed value.
-   - `Pledge.__str__()` - Return a readable supporter-to-campaign label for administration and logs.
- Class `SponsorStatus` - Enumerate the stable database/API values for SponsorStatus.
- Class `SponsorCommitment` - Persist SponsorCommitment state and enforce its domain-level invariants.
-   - `SponsorCommitment.active_statuses()` - Return sponsor states that still count toward the campaign funding threshold.
- Class `CampaignEvent` - Persist CampaignEvent state and enforce its domain-level invariants.
- Class `IntegrationSyncStatus` - Enumerate the stable database/API values for IntegrationSyncStatus.
- Class `ExternalResourceLink` - Persist ExternalResourceLink state and enforce its domain-level invariants.
- Class `IntegrationWebhookStatus` - Enumerate the stable database/API values for IntegrationWebhookStatus.
- Class `IntegrationWebhookEvent` - Persist IntegrationWebhookEvent state and enforce its domain-level invariants.

### `backend/gigs/payments.py`

Abstracts refundable deposit, capture, refund, and Stripe client-secret operations behind a provider interface.

- Class `PaymentResult` - Carry the provider reference, status, and browser client secret returned by a deposit request.
- Class `PaymentProvider` - Define the payment operations required by the campaign service layer.
-   - `PaymentProvider.collect_refundable_deposit()` - Create a refundable supporter deposit and return the stable provider reference needed for later capture or refund.
-   - `PaymentProvider.refund()` - Reverse the referenced deposit, optionally limiting the refund to a specific amount.
-   - `PaymentProvider.finalize()` - Finalize or capture a supporter commitment after the campaign reaches its confirmation requirements.
-   - `PaymentProvider.get_client_secret()` - Recover the browser client secret for an idempotently reused pending payment.
- Class `FakePaymentProvider` - Provide deterministic payment behavior for tests and local development.
-   - `FakePaymentProvider.collect_refundable_deposit()` - Create a deterministic in-memory payment result for local development and tests.
-   - `FakePaymentProvider.refund()` - Record a successful fake refund without contacting an external gateway.
-   - `FakePaymentProvider.finalize()` - Record a successful fake finalization without contacting an external gateway.
-   - `FakePaymentProvider.get_client_secret()` - Return the deterministic client secret associated with a fake payment reference.
- Class `StripePaymentProvider` - Implement refundable deposits, capture, refunds, and retrieval through Stripe PaymentIntents.
-   - `StripePaymentProvider.__init__()` - Initialize the Stripe SDK with the configured secret key.
-   - `StripePaymentProvider.collect_refundable_deposit()` - Create a manual-capture Stripe PaymentIntent used as the supporter's refundable commitment.
-   - `StripePaymentProvider.refund()` - Issue a Stripe refund for the referenced PaymentIntent or charge.
-   - `StripePaymentProvider.finalize()` - Capture the Stripe PaymentIntent after artist and venue confirmation.
-   - `StripePaymentProvider.get_client_secret()` - Retrieve an existing Stripe PaymentIntent and return its client secret.
- Function `get_payment_provider()` - Select the configured fake or Stripe payment adapter and fail fast on invalid configuration.

### `backend/gigs/permissions.py`

Defines object-level authorization for campaign owners and privileged staff users.

- Class `IsCampaignOwnerOrStaff` - Protect campaign mutations while allowing owners and privileged staff.
-   - `IsCampaignOwnerOrStaff.has_object_permission()` - Allow campaign mutations only to the owning organizer or privileged staff.

### `backend/gigs/serializers.py`

Validates and converts API payloads between JSON representations and Django domain objects.

- Class `CampaignSerializer` - Validate and translate Campaign API payloads between JSON and domain objects.
-   - `CampaignSerializer.get_owner()` - Expose a compact owner identity without leaking the full Django user record.
-   - `CampaignSerializer.validate_deadline()` - Reject campaign deadlines that are not in the future.
-   - `CampaignSerializer.validate()` - Validate goal-specific target fields and normalize campaign input as one coherent contract.
- Class `GigUserProfileUpdateSerializer` - Validate and translate GigUserProfileUpdate API payloads between JSON and domain objects.
-   - `GigUserProfileUpdateSerializer.validate()` - Require at least one editable profile field and reject unsupported account types.
- Class `PledgeCreateSerializer` - Validate and translate PledgeCreate API payloads between JSON and domain objects.
- Class `PledgeSerializer` - Validate and translate Pledge API payloads between JSON and domain objects.
- Class `SponsorCreateSerializer` - Validate and translate SponsorCreate API payloads between JSON and domain objects.
- Class `SponsorSerializer` - Validate and translate Sponsor API payloads between JSON and domain objects.
- Class `ConfirmationSerializer` - Validate and translate Confirmation API payloads between JSON and domain objects.
- Class `FinalizeSerializer` - Validate and translate Finalize API payloads between JSON and domain objects.
- Class `FacebookAccessTokenSerializer` - Validate and translate FacebookAccessToken API payloads between JSON and domain objects.
- Class `FacebookShareLinkSerializer` - Validate and translate FacebookShareLink API payloads between JSON and domain objects.
- Class `FacebookPagePublishSerializer` - Validate and translate FacebookPagePublish API payloads between JSON and domain objects.
- Class `FacebookConversionSerializer` - Validate and translate FacebookConversion API payloads between JSON and domain objects.

### `backend/gigs/services.py`

Implements transactional campaign lifecycle rules, threshold evaluation, confirmations, payment finalization, expiration, and refunds.

- Class `CampaignStateError` - Signal that a requested campaign transition violates the lifecycle state machine.
- Function `log_event()` - Append an immutable campaign audit event with structured context for troubleshooting and integrations.
- Function `_send_meta_event_safely()` - Send optional Meta attribution after commit without allowing advertising failures to break core business transactions.
- Function `launch_campaign()` - Move a valid draft campaign into supporter collection while holding a database row lock.
- Function `create_pledge()` - Create or resume an idempotent supporter pledge, collect an optional deposit, and re-evaluate the threshold.
- Function `create_sponsorship()` - Record a sponsor commitment, audit it, and re-evaluate whether the campaign target is reached.
- Function `evaluate_threshold_locked()` - Advance a locked collecting campaign to TARGET_REACHED when its configured threshold is satisfied.
- Function `confirm_artist()` - Record artist confirmation after demand reaches the threshold and advance the confirmation state.
- Function `confirm_venue()` - Record venue confirmation after demand reaches the threshold and advance the confirmation state.
- Function `finalize_campaign()` - Finalize all eligible payments and mark a fully confirmed campaign ready for production.
- Function `fail_and_refund_campaign()` - Move an unsuccessful campaign through refunding, reverse eligible payments, and record any failures.
- Function `expire_due_campaigns()` - Find collecting campaigns past their deadline and fail/refund only those that missed the target.

### `backend/gigs/signals.py`

Responds to Django and social-authentication signals to create or update related application profile data.

- Function `ensure_gig_profile()` - Create the application-specific profile whenever a Django user is created.
- Function `_synchronize_profile()` - Copy trusted social-account details such as avatar and display name into the local profile.

### `backend/gigs/social_auth.py`

Synchronizes social-account identity data into the application profile while preserving local ownership rules.

- Class `SocialProvider` - Describe one supported social-login provider and its required configuration.
- Function `provider_enabled()` - Return whether a social provider has credentials and a resolvable django-allauth login route.
- Function `provider_login_path()` - Resolve the django-allauth login URL for one supported provider.
- Function `provider_payload()` - Build the frontend provider list with labels, routes, availability, and required configuration.
- Function `extract_avatar()` - Normalize avatar URLs from the different payload shapes returned by social providers.

### `backend/gigs/tests/__init__.py`

Marks the gigs automated-test suite as an importable Python package.

### `backend/gigs/tests/test_auth.py`

Verifies authentication configuration, session profile, logout, provider redirects, and ownership behavior.

- Function `campaign_payload()` - Build a valid campaign API payload and merge caller-provided overrides.
- Class `TestSocialAuth` - Exercise TestSocialAuth behavior, edge cases, and failure handling with isolated tests.
-   - `TestSocialAuth.test_health_endpoint()` - Verify that health endpoint.
-   - `TestSocialAuth.test_avatar_extraction()` - Verify that avatar extraction.
-   - `TestSocialAuth.test_provider_enabled()` - Verify that provider enabled.
-   - `TestSocialAuth.test_provider_requires_credentials()` - Verify that provider requires credentials.
-   - `TestSocialAuth.test_provider_routes()` - Verify that provider routes.
-   - `TestSocialAuth.test_provider_payload_lists_all_providers()` - Verify that provider payload lists all providers.
-   - `TestSocialAuth.test_provider_without_registered_route_is_disabled()` - Verify that provider without registered route is disabled.
-   - `TestSocialAuth.test_auth_config_anonymous_and_profile_update()` - Verify that auth config anonymous and profile update.
-   - `TestSocialAuth.test_auth_config_serializes_social_account_and_avatar()` - Verify that auth config serializes social account and avatar.
-   - `TestSocialAuth.test_profile_signal_sync()` - Verify that profile signal sync.
-   - `TestSocialAuth.test_authenticated_campaign_is_owned()` - Verify that authenticated campaign is owned.
-   - `TestSocialAuth.test_campaign_management_requires_owner_but_allows_staff()` - Verify that campaign management requires owner but allows staff.
-   - `TestSocialAuth.test_authenticated_pledge_and_sponsor_are_linked_to_user()` - Verify that authenticated pledge and sponsor are linked to user.

### `backend/gigs/tests/test_campaign_flow.py`

Exercises the end-to-end campaign lifecycle from creation and launch through pledges, threshold evaluation, confirmation, expiry, and refunds.

- Class `DemandCampaignFlowTests` - Exercise DemandCampaignFlow behavior, edge cases, and failure handling with isolated tests.
-   - `DemandCampaignFlowTests.make_campaign()` - Create a campaign test fixture with valid defaults and optional field overrides.
-   - `DemandCampaignFlowTests.pledge_data()` - Build a valid pledge payload and merge test-specific overrides.
-   - `DemandCampaignFlowTests.test_threshold_confirmation_and_finalization()` - Verify that threshold confirmation and finalization.
-   - `DemandCampaignFlowTests.test_failed_campaign_refunds_paid_and_cancels_nonfinancial_support()` - Verify that failed campaign refunds paid and cancels nonfinancial support.
-   - `DemandCampaignFlowTests.test_idempotency_is_scoped_to_campaign()` - Verify that idempotency is scoped to campaign.
-   - `DemandCampaignFlowTests.test_sponsor_commitment_can_reach_money_goal()` - Verify that sponsor commitment can reach money goal.
-   - `DemandCampaignFlowTests.test_confirmation_is_blocked_before_threshold()` - Verify that confirmation is blocked before threshold.
-   - `DemandCampaignFlowTests.test_launch_rejects_expired_campaign()` - Verify that launch rejects expired campaign.
-   - `DemandCampaignFlowTests.test_slug_is_unique()` - Verify that slug is unique.

### `backend/gigs/tests/test_facebook.py`

Verifies Facebook share-link construction, campaign tracking parameters, and public Meta integration behavior.

- Class `FacebookLinkTests` - Exercise FacebookLink behavior, edge cases, and failure handling with isolated tests.
-   - `FacebookLinkTests.test_share_link_tracks_and_encodes_group_and_referral()` - Verify that share link tracks and encodes group and referral.

### `backend/gigs/tests/test_facebook_coverage.py`

Covers Meta Graph success, validation, pagination, provider errors, conversion events, and failure boundaries not exercised by the primary Facebook tests.

- Class `FacebookIntegrationCoverageTests` - Exercise FacebookIntegrationCoverage behavior, edge cases, and failure handling with isolated tests.
-   - `FacebookIntegrationCoverageTests.response()` - Build a lightweight HTTP response double with the requested payload and status code.
-   - `FacebookIntegrationCoverageTests.test_graph_url_normalizes_slashes()` - Verify that graph URL normalizes slashes.
-   - `FacebookIntegrationCoverageTests.test_request_json_get_and_post()` - Verify that request json get and post.
-   - `FacebookIntegrationCoverageTests.test_request_json_maps_transport_and_payload_errors()` - Verify that request json maps transport and payload errors.
-   - `FacebookIntegrationCoverageTests.test_share_link_without_app_id()` - Verify that share link without app ID.
-   - `FacebookIntegrationCoverageTests.test_verify_user_requires_app_configuration()` - Verify that verify user requires app configuration.
-   - `FacebookIntegrationCoverageTests.test_verify_user_rejects_invalid_or_wrong_app_token()` - Verify that verify user rejects invalid or wrong app token.
-   - `FacebookIntegrationCoverageTests.test_verify_user_returns_normalized_profile()` - Verify that verify user returns normalized profile.
-   - `FacebookIntegrationCoverageTests.test_list_pages_and_publish()` - Verify that list pages and publish.
-   - `FacebookIntegrationCoverageTests.test_sha256_normalizes_email()` - Verify that sha256 normalizes email.
-   - `FacebookIntegrationCoverageTests.test_conversion_event_is_optional()` - Verify that conversion event is optional.
-   - `FacebookIntegrationCoverageTests.test_conversion_event_builds_complete_payload()` - Verify that conversion event builds complete payload.
-   - `FacebookIntegrationCoverageTests.test_conversion_event_without_optional_user_or_value_data()` - Verify that conversion event without optional user or value data.

### `backend/gigs/tests/test_model_serializer_coverage.py`

Exercises model validation, computed progress, string representations, serializer rules, and boundary conditions across campaign entities.

- Class `ModelAndSerializerCoverageTests` - Exercise ModelAndSerializerCoverage behavior, edge cases, and failure handling with isolated tests.
-   - `ModelAndSerializerCoverageTests.make_campaign()` - Create a campaign test fixture with valid defaults and optional field overrides.
-   - `ModelAndSerializerCoverageTests.test_campaign_clean_validation_branches()` - Verify that campaign clean validation branches.
-   - `ModelAndSerializerCoverageTests.test_slug_fallback_and_string_representations()` - Verify that slug fallback and string representations.
-   - `ModelAndSerializerCoverageTests.test_target_and_progress_for_each_goal_type()` - Verify that target and progress for each goal type.
-   - `ModelAndSerializerCoverageTests.test_campaign_serializer_remaining_validation_paths()` - Verify that campaign serializer remaining validation paths.

### `backend/gigs/tests/test_payments.py`

Verifies fake and Stripe payment-provider selection, idempotent deposits, finalization, client-secret recovery, and refund behavior.

- Class `PaymentProviderTests` - Exercise PaymentProvider behavior, edge cases, and failure handling with isolated tests.
-   - `PaymentProviderTests.test_fake_provider()` - Verify that fake provider.
-   - `PaymentProviderTests.test_provider_selection_fake()` - Verify that provider selection fake.
-   - `PaymentProviderTests.test_provider_selection_requires_key()` - Verify that provider selection requires key.
-   - `PaymentProviderTests.test_stripe_provider_operations()` - Verify that stripe provider operations.
-   - `PaymentProviderTests.test_provider_selection_stripe()` - Verify that provider selection stripe.

### `backend/gigs/tests/test_process_tasks.py`

Verifies SQS worker argument handling, supported and unknown job dispatch, acknowledgements, one-shot mode, and retry-preserving failures.

- Class `ProcessTasksCommandTests` - Exercise ProcessTasksCommand behavior, edge cases, and failure handling with isolated tests.
-   - `ProcessTasksCommandTests.setUp()` - Create reusable fixtures and mocks required by each test in this class.
-   - `ProcessTasksCommandTests.test_requires_queue_url()` - Verify that requires queue URL.
-   - `ProcessTasksCommandTests.test_expiry_job_runs_service_and_deletes_message()` - Verify that expiry job runs service and deletes message.
-   - `ProcessTasksCommandTests.test_unknown_job_is_acknowledged()` - Verify that unknown job is acknowledged.
-   - `ProcessTasksCommandTests.test_failure_is_not_deleted_so_sqs_can_retry()` - Verify that failure is not deleted so SQS can retry.
-   - `ProcessTasksCommandTests.test_once_mode_polls_exactly_once()` - Verify that once mode polls exactly once.

### `backend/gigs/tests/test_serializers.py`

Verifies API serializer validation for campaign creation, pledges, sponsors, and external integration inputs.

- Class `CampaignSerializerTests` - Exercise CampaignSerializer behavior, edge cases, and failure handling with isolated tests.
-   - `CampaignSerializerTests.base_data()` - Return a valid baseline serializer payload for focused validation tests.
-   - `CampaignSerializerTests.test_normalizes_currency()` - Verify that normalizes currency.
-   - `CampaignSerializerTests.test_rejects_zero_amount_for_money_goal()` - Verify that rejects zero amount for money goal.

### `backend/gigs/tests/test_service_edge_coverage.py`

Covers service-layer idempotency, invalid lifecycle transitions, race-resistant threshold evaluation, expiry, refunds, and integration side effects.

- Class `ServiceEdgeCoverageTests` - Exercise ServiceEdgeCoverage behavior, edge cases, and failure handling with isolated tests.
-   - `ServiceEdgeCoverageTests.make_campaign()` - Create a campaign test fixture with valid defaults and optional field overrides.
-   - `ServiceEdgeCoverageTests.pledge_data()` - Build a valid pledge payload and merge test-specific overrides.
-   - `ServiceEdgeCoverageTests.test_meta_event_wrapper_swallows_only_meta_errors()` - Verify that meta event wrapper swallows only meta errors.
-   - `ServiceEdgeCoverageTests.test_launch_and_create_reject_invalid_states_and_expired_deadline()` - Verify that launch and create reject invalid states and expired deadline.
-   - `ServiceEdgeCoverageTests.test_existing_pending_stripe_pledge_returns_client_secret()` - Verify that existing pending stripe pledge returns client secret.
-   - `ServiceEdgeCoverageTests.test_paid_pledge_can_remain_pending_and_schedule_checkout_event()` - Verify that paid pledge can remain pending and schedule checkout event.
-   - `ServiceEdgeCoverageTests.test_commitment_schedules_lead_and_threshold_noop()` - Verify that commitment schedules lead and threshold noop.
-   - `ServiceEdgeCoverageTests.test_artist_and_venue_confirmation_edge_paths()` - Verify that artist and venue confirmation edge paths.
-   - `ServiceEdgeCoverageTests.test_finalize_rejects_unconfirmed_campaign()` - Verify that finalize rejects unconfirmed campaign.
-   - `ServiceEdgeCoverageTests.test_failure_flow_rejects_terminal_campaign()` - Verify that failure flow rejects terminal campaign.
-   - `ServiceEdgeCoverageTests.test_pledge_refund_failure_leaves_campaign_refunding()` - Verify that pledge refund failure leaves campaign refunding.
-   - `ServiceEdgeCoverageTests.test_paid_sponsor_without_reference_is_canceled()` - Verify that paid sponsor without reference is canceled.
-   - `ServiceEdgeCoverageTests.test_paid_sponsor_refund_success_and_failure()` - Verify that paid sponsor refund success and failure.
-   - `ServiceEdgeCoverageTests.test_expire_due_campaigns_only_fails_unmet_collecting_campaigns()` - Verify that expire due campaigns only fails unmet collecting campaigns.

### `backend/gigs/urls.py`

Maps application API paths to view sets, authentication endpoints, payment webhooks, and integration webhooks.

### `backend/gigs/views.py`

Exposes REST and webhook endpoints that translate HTTP requests into validated domain-service operations.

- Class `CampaignViewSet` - Expose REST endpoints and lifecycle actions for Campaign resources.
-   - `CampaignViewSet.get_permissions()` - Apply public read access while protecting campaign-changing actions with owner/staff authorization.
-   - `CampaignViewSet.perform_create()` - Assign the authenticated organizer as owner when a new campaign is created.
-   - `CampaignViewSet.launch()` - Validate the launch action and invoke the transactional campaign state transition.
-   - `CampaignViewSet.pledge()` - Validate supporter input, create the idempotent pledge, and return payment details when required.
-   - `CampaignViewSet.sponsor()` - Validate and record a sponsor commitment for the selected campaign.
-   - `CampaignViewSet.confirm_artist_action()` - Record artist confirmation through the campaign service layer.
-   - `CampaignViewSet.confirm_venue_action()` - Record venue confirmation through the campaign service layer.
-   - `CampaignViewSet.finalize()` - Finalize a campaign only after the required artist and venue confirmations.
-   - `CampaignViewSet.refund()` - Fail the campaign and initiate refunds through the configured payment provider.
-   - `CampaignViewSet.facebook_share_link()` - Generate a tracked Facebook share URL without publishing content automatically.
-   - `CampaignViewSet.facebook_track_conversion()` - Forward a validated campaign conversion event to Meta for attribution.
-   - `CampaignViewSet.facebook_publish_page()` - Publish the campaign to a Facebook Page the organizer manages.
- Function `facebook_config()` - Return Meta app settings and supported Facebook integration capabilities to the frontend.
- Function `facebook_login()` - Verify a Facebook access token and return the normalized organizer identity.
- Function `facebook_pages()` - Return Pages available to the organizer represented by the supplied Facebook token.
- Function `campaign_share_page()` - Render share-friendly Open Graph metadata and redirect visitors to the frontend campaign.
- Function `stripe_webhook()` - Verify Stripe webhook signatures and synchronize pledge payment status idempotently.
- Function `vibesmeet_config()` - Describe whether the optional VibesMeet bridge is configured and which capabilities are enabled.
- Function `vibesmeet_webhook()` - Verify, deduplicate, persist, and apply inbound VibesMeet integration events.

### `backend/integrations/__init__.py`

External partner integrations.

### `backend/integrations/vibesmeet/__init__.py`

Contract-first VibesMeet integration bridge.

### `backend/integrations/vibesmeet/client.py`

Implements the signed, idempotent HTTP client used to exchange event, reservation, order, attendance, and payout data with VibesMeet.

- Class `VibesMeetConfig` - Hold and validate connection settings for the optional VibesMeet bridge.
-   - `VibesMeetConfig.validate()` - Validate the bridge base URL, credentials, timeout, and webhook secret before use.
- Class `VibesMeetClient` - Encapsulate authenticated HTTP communication with the VibesMeet partner API.
-   - `VibesMeetClient.__init__()` - Store validated bridge configuration and prepare the reusable HTTP client boundary.
-   - `VibesMeetClient.health()` - Read the remote VibesMeet health endpoint.
-   - `VibesMeetClient.capabilities()` - Discover which integration capabilities the connected VibesMeet tenant exposes.
-   - `VibesMeetClient.create_draft_event()` - Create a VibesMeet draft event from the validated demand-campaign handoff contract.
-   - `VibesMeetClient.update_event()` - Update a previously linked VibesMeet event with an idempotent request.
-   - `VibesMeetClient.create_reservation_claims()` - Send supporter reservation claims to the linked VibesMeet event.
-   - `VibesMeetClient.request_publish()` - Ask VibesMeet to publish an event after local confirmation requirements are met.
-   - `VibesMeetClient.get_event()` - Fetch the current remote event representation.
-   - `VibesMeetClient.attendance_summary()` - Fetch aggregated attendance data for reconciliation and reporting.
-   - `VibesMeetClient.order_summary()` - Fetch aggregated order data for reconciliation and reporting.
-   - `VibesMeetClient.payout_summary()` - Fetch aggregated payout data for reconciliation and reporting.
-   - `VibesMeetClient._request()` - Send one authenticated VibesMeet request with correlation, idempotency, timeout, and controlled error mapping.

### `backend/integrations/vibesmeet/events.py`

Proposed VibesMeet webhook event names.

### `backend/integrations/vibesmeet/exceptions.py`

Defines typed VibesMeet validation, authentication, conflict, and remote-response errors for predictable boundary handling.

- Class `VibesMeetError` - Base exception for failures at the VibesMeet integration boundary.
- Class `VibesMeetValidationError` - Signal invalid local input before any VibesMeet request is sent.
- Class `VibesMeetAuthError` - Signal rejected or missing VibesMeet authentication.
- Class `VibesMeetConflictError` - Signal an idempotency or remote-state conflict returned by VibesMeet.
- Class `VibesMeetRemoteError` - Preserve an unexpected VibesMeet HTTP response for controlled handling and diagnostics.
-   - `VibesMeetRemoteError.__init__()` - Capture the remote status code and response body alongside the integration error message.

### `backend/integrations/vibesmeet/signing.py`

Builds and verifies HMAC signatures used to authenticate VibesMeet webhook and API payloads.

- Function `build_signature()` - Create the timestamped HMAC signature used to authenticate outbound webhook payloads.
- Function `verify_signature()` - Validate timestamp freshness and compare the webhook HMAC in constant time.

### `backend/integrations/vibesmeet/tests/__init__.py`

Marks the VibesMeet contract and edge-case tests as an importable Python package.

### `backend/integrations/vibesmeet/tests/test_contract.py`

Validates VibesMeet request contracts, canonical signing, webhook verification, idempotency keys, and typed client responses.

- Class `VibesMeetContractTests` - Exercise VibesMeetContract behavior, edge cases, and failure handling with isolated tests.
-   - `VibesMeetContractTests.test_handoff_serializes_and_validates()` - Verify that handoff serializes and validates.
-   - `VibesMeetContractTests.test_signed_webhook_parses()` - Verify that signed webhook parses.

### `backend/integrations/vibesmeet/tests/test_edge_cases.py`

Exercises VibesMeet malformed payloads, timestamp skew, authentication failures, duplicate events, conflicts, retries, and unexpected remote responses.

- Function `valid_ticket()` - Build a valid ticket fixture for contract and edge-case tests.
- Function `valid_handoff()` - Build a valid handoff fixture for contract and edge-case tests.
- Function `test_ticket_validation_errors()` - Verify that ticket validation errors.
- Function `test_ticket_serializes_dates_and_currency()` - Verify that ticket serializes dates and currency.
- Function `test_reservation_validation_errors()` - Verify that reservation validation errors.
- Function `test_reservation_serialization_optional_dates()` - Verify that reservation serialization optional dates.
- Function `test_split_validation_errors()` - Verify that split validation errors.
- Function `test_split_to_dict()` - Verify that split to dict.
- Function `test_handoff_validation_errors()` - Verify that handoff validation errors.
- Function `test_handoff_rejects_bad_nested_values_and_split_total()` - Verify that handoff rejects bad nested values and split total.
- Function `test_handoff_full_serialization()` - Verify that handoff full serialization.
- Function `test_signature_success_and_failures()` - Verify that signature success and failures.
- Function `signed_payload()` - Create a canonical signed webhook body and headers for verification tests.
- Function `test_webhook_unknown_and_defaults()` - Verify that webhook unknown and defaults.
- Function `test_webhook_validation_errors()` - Verify that webhook validation errors.
- Function `test_config_validation_errors()` - Verify that config validation errors.
- Function `test_client_routes_and_request_success()` - Verify that client routes and request success.
- Function `response()` - Build a lightweight HTTP response double with the requested payload and status code.
- Function `test_low_level_request_success_empty_invalid_and_network()` - Verify that low level request success empty invalid and network.
- Function `test_low_level_http_errors()` - Verify that low level http errors.

### `backend/integrations/vibesmeet/types.py`

Defines validated transport dataclasses for tickets, reservations, revenue splits, and event handoff payloads.

- Function `_money()` - Normalize monetary input to a two-decimal Decimal value.
- Class `TicketTypePlan` - Describe one ticket tier included in the VibesMeet event handoff.
-   - `TicketTypePlan.validate()` - Validate ticket identifiers, quantities, and non-negative prices before handoff.
-   - `TicketTypePlan.to_dict()` - Serialize the ticket plan into the JSON shape expected by VibesMeet.
- Class `ReservationClaim` - Describe supporter inventory reserved before the final event is published.
-   - `ReservationClaim.validate()` - Validate supporter reservation quantity and optional expiration timestamps.
-   - `ReservationClaim.to_dict()` - Serialize a reservation claim while omitting optional values that are not set.
- Class `RevenueSplit` - Describe one recipient and percentage in the event revenue allocation.
-   - `RevenueSplit.validate()` - Validate the payout recipient and percentage boundaries.
-   - `RevenueSplit.to_dict()` - Serialize one revenue split using stable decimal formatting.
- Class `EventHandoff` - Represent the validated local-to-VibesMeet event creation contract.
-   - `EventHandoff.validate()` - Validate nested tickets, reservations, revenue splits, dates, currency, and total split percentage.
-   - `EventHandoff.to_dict()` - Serialize the complete event handoff contract into API-ready primitives.

### `backend/integrations/vibesmeet/webhooks.py`

Verifies and parses inbound VibesMeet webhook envelopes before business processing.

- Class `WebhookEnvelope` - Represent a verified, typed inbound VibesMeet webhook envelope.
- Function `parse_verified_webhook()` - Verify the webhook signature, validate its envelope, and return a typed integration event.

### `backend/manage.py`

Provides Django command-line entry points for development, migrations, administration, and operational commands.

## Root configuration

### `docker-compose.yml`

Defines the local PostgreSQL, Django, and React/Nginx stack, including health dependencies, environment boundaries, persistent data, and developer ports.

### `docs/openapi/vibesmeet-bridge.openapi.yaml`

Defines the proposed authenticated VibesMeet partner API, idempotency headers, request/response schemas, and webhook contract that must be confirmed before production use.

## Frontend

### `frontend/src/App.tsx`

Coordinates the single-page application, campaign loading, authentication state, campaign creation, and selected-campaign views.

- Function `App` - Render the application shell and coordinate campaign loading, creation, launch, pledges, sponsorships, and integration initialization.
- Function `reload` - Refresh the campaign list and surface API connectivity errors without discarding the current page shell.
- Function `create` - Persist a new campaign and prepend it to local state so the organizer sees it immediately.
- Function `launch` - Move a draft campaign into demand collection, then reload server-calculated status and progress.
- Function `pledge` - Submit an idempotent supporter commitment, refresh totals, and return any Stripe client secret.
- Function `sponsor` - Record a sponsor commitment and refresh campaign funding progress from the authoritative API.

### `frontend/src/api.ts`

Provides typed browser functions for calling campaign, authentication, Facebook, Stripe, and VibesMeet API endpoints.

- Function `request` - Send one credentialed JSON request, normalize empty bodies, and convert non-2xx responses into Error objects.
- Function `csrfHeaders` - Return the Django CSRF header from the browser cookie, falling back to the token returned by the auth configuration endpoint.
- Constant `api` - Group every browser-facing backend operation behind typed methods with shared credentials, CSRF, and error handling.

### `frontend/src/components/AuthPanel.tsx`

Displays authentication state, starts OAuth login/link flows, edits account type, and ends the current session.

- Constant `BACKEND_BASE` - Derive the Django origin from VITE_API_BASE so allauth form posts bypass the /api prefix.
- Function `startProviderLogin` - Submit a CSRF-protected form to django-allauth for either a new login or an additional account connection.
- Function `AuthPanel` - Render anonymous provider buttons or the authenticated profile, linked identities, account-type selector, and sign-out control.
- Function `load` - Reload authentication configuration after initial render, profile changes, linking, or logout.

### `frontend/src/components/CampaignCard.tsx`

Presents campaign status and progress, captures supporter/sponsor input, completes deposits, and exposes sharing integrations.

- Interface `Props` - Receive one campaign plus callbacks for state transitions, commitments, sponsorships, and authoritative reloads.
- Function `CampaignCard` - Render lifecycle status, threshold metrics, confirmation state, pledge/sponsor forms, Stripe deposit completion, and social sharing.
- Constant `money` - Format server-supplied decimal strings in the campaign currency for readable progress and target values.
- Function `pledge` - Submit one idempotent supporter commitment and open Stripe only when the backend returns a client secret.
- Function `submitSponsor` - Validate and submit a sponsor commitment, then reset only the form fields after success.
- Function `share` - Use the native share sheet when available, otherwise copy the public campaign URL to the clipboard.

### `frontend/src/components/CreateCampaignForm.tsx`

Collects a proposed gig seed, goal, deadline, organizer details, and optional Facebook community links.

- Interface `Props` - Accept the async creation callback owned by the application shell.
- Function `inThirtyDays` - Return a local datetime value thirty days ahead for the form deadline default.
- Function `CreateCampaignForm` - Render controlled campaign fields, normalize date/currency values, and submit one validated draft to the API.
- Function `submit` - Prevent native navigation, convert the local deadline to ISO format, and preserve errors for organizer correction.

### `frontend/src/components/DepositPayment.tsx`

Confirms a Stripe PaymentIntent for a refundable supporter deposit and reports completion to the campaign card.

- Interface `Props` - Receive the callback invoked after Stripe confirms the supporter deposit.
- Function `DepositPayment` - Render Stripe PaymentElement, prevent duplicate submission, and display provider validation or confirmation errors.
- Function `submit` - Confirm the existing PaymentIntent without creating a second pledge or charge.

### `frontend/src/components/FacebookIntegration.tsx`

Creates tracked Facebook links, connects an organizer account, lists managed Pages, and publishes campaign messages.

- Interface `Props` - Receive the active campaign and a callback for presenting integration status to the surrounding card.
- Function `FacebookIntegration` - Coordinate manual Group sharing, tracked-link copying, Facebook Login, managed-Page discovery, and Page publication.
- Function `generateLink` - Ask the backend to sign a tracked URL carrying community and referral attribution.
- Function `shareToFacebook` - Open Facebook Share in a popup using the tracked URL; Group selection remains a user-controlled Meta action.
- Function `copyTrackedLink` - Copy the same attributed campaign URL for Facebook Events, Groups, Messenger, WhatsApp, or other communities.
- Function `connectFacebook` - Obtain a user token in the browser, verify it on the backend, and load Pages the organizer may manage.
- Function `publishToPage` - Publish a tracked campaign message to the selected managed Page through the backend Graph API adapter.

### `frontend/src/facebook.ts`

Loads the Facebook JavaScript SDK and wraps login and browser-event tracking behavior.

- Interface `Window` - Extend Window with the minimal Facebook SDK surface used by this application.
- Interface `FacebookLoginResponse` - Model the subset of Facebook Login response fields needed to extract the user access token.
- Function `loadFacebookSdk` - Load and initialize the Facebook JavaScript SDK once per app ID, reusing an existing script when present.
- Function `loginWithFacebook` - Request the Page-management scopes and resolve only with a user token approved by the organizer.

### `frontend/src/main.tsx`

Bootstraps React, attaches the application to the HTML root element, and enables development diagnostics.

### `frontend/src/meta.ts`

Initializes Meta Pixel and emits browser conversion events with deduplication identifiers.

- Interface `Window` - Extend Window with the Meta Pixel queue function installed by the external script.
- Function `initMetaPixel` - Initialize Meta Pixel exactly once per pixel ID, queue calls until the SDK loads, and record the initial PageView.
- Function `trackMetaEvent` - Emit a browser conversion event and include eventID when server-side Conversions API deduplication is used.

### `frontend/src/stripe.ts`

Initializes Stripe.js and exposes the configured publishable-key client to payment components.

- Constant `publishableKey` - Read only Stripe's browser-safe publishable key; the secret key remains on the backend.
- Constant `stripePromise` - Load one reusable Stripe.js client, or expose null so payment UI stays disabled when no key is configured.

### `frontend/src/types.ts`

Defines shared TypeScript contracts used by React components and API functions.

- Type `GoalType` - Select whether success is measured by attendees, committed money, or both thresholds.
- Interface `Campaign` - Represent the complete campaign API response, including owner identity, lifecycle state, calculated totals, and social links.
- Interface `CampaignCreate` - Define the draft-campaign fields accepted by the creation endpoint before server-side ownership and status are assigned.
- Interface `PledgeInput` - Define one supporter commitment, including the idempotency and attribution fields that make retries and marketing measurement safe.
- Interface `PledgeResult` - Return the persisted pledge identity/status and an optional Stripe client secret for completing a deposit.
- Interface `SponsorInput` - Define the sponsor identity, contact, committed amount, and requested benefits sent to the campaign API.
- Interface `FacebookConfig` - Expose only public Meta identifiers and capability flags needed by the browser; app secrets remain server-side.
- Interface `FacebookProfile` - Represent the normalized Facebook identity returned after the backend verifies the user token.
- Interface `FacebookPage` - Represent a managed Facebook Page and the scoped token used only for an explicit organizer publication request.
- Interface `FacebookShareLink` - Carry the attributed campaign URL and the Facebook share-dialog URL built around it.
- Interface `VibesMeetConfig` - Describe optional VibesMeet bridge readiness and the integration capabilities implemented by this repository.
- Type `AccountType` - Enumerate marketplace roles supported by user profiles and future matching workflows.
- Interface `AuthProvider` - Describe one social provider, its allauth routes, and whether configuration is complete enough to enable it.
- Interface `AuthUser` - Represent the editable application profile plus linked social identities for the signed-in user.
- Interface `AuthConfig` - Return session state, provider availability, CSRF protection, and account-type choices required by the authentication panel.

### `frontend/src/vite-env.d.ts`

Loads Vite client type declarations so import.meta.env and asset imports are checked by TypeScript.

### `frontend/vite.config.ts`

Configures the Vite development server, React transform, build behavior, and local API proxy.

## Repository scripts

### `scripts/run_all_tests.sh`

Runs the complete application, infrastructure, and security validation sequence from one entry point.

### `scripts/run_full_tests.sh`

Runs application-focused checks, Django tests and coverage, frontend builds, and Docker Compose validation.

### `scripts/security_scan.sh`

Runs static security, dependency, secret, container, workflow, and infrastructure-as-code checks.

### `scripts/static_checks.py`

Dependency-free structural validation for the Demand Gig MVP package.

- Function `check()` - Record one dependency-free validation result and increment the shared pass/fail counters.
- Function `check_python()` - Parse every Python source file to catch syntax errors without importing project dependencies.
- Function `check_json()` - Load a JSON file and report malformed configuration or contract data.
- Function `check_compose()` - Verify the required Compose services and database health dependency.
- Function `check_migrations()` - Confirm that Django migration numbers form the expected sequential chain.
- Function `png_dimensions()` - Read PNG header dimensions without requiring an imaging dependency.
- Function `check_screenshots()` - Validate screenshot files, dimensions, and the combined PDF artifact.
- Function `check_pdf()` - Confirm the PDF signature, EOF marker, and renderer-readable structure.
- Function `check_contracts()` - Parse and validate the proposed OpenAPI and JSON integration contracts.
- Function `check_required_files()` - Verify that the repository contains every required application, document, and automation file.
- Function `check_vibesmeet_bridge()` - Check the bridge client, webhook verification, ownership boundaries, and supporting contracts.
- Function `main()` - Run the module as a command-line validation entry point and return a process status.

### `scripts/validate_workflows.py`

Validate the repository's GitHub Actions files without GitHub API access.

- Function `load_workflow()` - Load a GitHub Actions workflow while preserving the YAML key named "on".
- Function `iter_steps()` - Yield every workflow step together with its job and step indexes for precise diagnostics.
- Function `validate_action_reference()` - Reject unpinned, mutable, or unsupported GitHub Action references.
- Function `main()` - Run the module as a command-line validation entry point and return a process status.

## Terraform and infrastructure tests

### `terraform/global/bootstrap/main.tf`

Creates secure S3 remote-state storage before the main environment can use that backend.

- `data aws_caller_identity.current` - Read the active AWS account identity for policies, names, and ownership checks.
- `resource aws_s3_bucket.state` - Creates an encrypted object-storage bucket for static assets, media, logs, or state.
- `resource aws_s3_bucket_versioning.state` - Retains prior object versions to support recovery and auditability.
- `resource aws_s3_bucket_public_access_block.state` - Prevents accidental public exposure through S3 ACLs or policies.
- `resource aws_s3_bucket_server_side_encryption_configuration.state` - Enforces server-side encryption for newly written objects.
- `resource aws_s3_bucket_policy.tls` - Applies resource-level access controls and transport requirements to the bucket.
- `output bucket` - Output `bucket`: Name of the remote-state S3 bucket created or validated by the bootstrap stack.

### `terraform/global/bootstrap/variables.tf`

Declares Terraform configuration for variables.

- `variable aws_region` - Input `aws_region`: AWS region in which regional workload resources are created.
- `variable environment` - Input `environment`: Deployment environment name or the container environment-variable map, according to module context.
- `variable project_name` - Input `project_name`: Stable project prefix used to name and tag shared AWS resources.

### `terraform/global/bootstrap/versions.tf`

Declares Terraform configuration for versions.

- `terraform terraform` - Define Terraform and provider compatibility before any resources are evaluated.
- `provider aws` - Configures the provider connection and any region-specific alias used by this stack.

### `terraform/main.tf`

Composes reusable AWS modules into the complete Demand Gig Engine environment.

- `locals locals` - Compute reusable derived values used throughout this file.
- `module kms` - Invokes the reusable kms module and passes this environment configuration into it.
- `module networking` - Invokes the reusable networking module and passes this environment configuration into it.
- `module security` - Invokes the reusable security module and passes this environment configuration into it.
- `module ecr` - Invokes the reusable ecr module and passes this environment configuration into it.
- `module static` - Invokes the reusable static module and passes this environment configuration into it.
- `module media` - Invokes the reusable media module and passes this environment configuration into it.
- `module acm_viewer` - Invokes the reusable acm viewer module and passes this environment configuration into it.
- `module acm_origin` - Invokes the reusable acm origin module and passes this environment configuration into it.
- `module waf` - Invokes the reusable waf module and passes this environment configuration into it.
- `module alb` - Invokes the reusable alb module and passes this environment configuration into it.
- `module cloudfront` - Invokes the reusable cloudfront module and passes this environment configuration into it.
- `module route53` - Invokes the reusable route53 module and passes this environment configuration into it.
- `module route53_origin` - Invokes the reusable route53 origin module and passes this environment configuration into it.
- `module database` - Invokes the reusable database module and passes this environment configuration into it.
- `module redis` - Invokes the reusable redis module and passes this environment configuration into it.
- `module sqs` - Invokes the reusable sqs module and passes this environment configuration into it.
- `module eventbridge` - Invokes the reusable eventbridge module and passes this environment configuration into it.
- `module secrets_manager` - Invokes the reusable secrets manager module and passes this environment configuration into it.
- `module ses` - Invokes the reusable ses module and passes this environment configuration into it.
- `module cluster` - Invokes the reusable cluster module and passes this environment configuration into it.
- `module backend` - Invokes the reusable backend module and passes this environment configuration into it.
- `module worker` - Invokes the reusable worker module and passes this environment configuration into it.
- `module migration` - Invokes the reusable migration module and passes this environment configuration into it.
- `module github_oidc` - Invokes the reusable github oidc module and passes this environment configuration into it.
- `module backup` - Invokes the reusable backup module and passes this environment configuration into it.
- `module cloudwatch` - Invokes the reusable cloudwatch module and passes this environment configuration into it.
- `module cloudtrail` - Invokes the reusable cloudtrail module and passes this environment configuration into it.
- `module guardduty` - Invokes the reusable guardduty module and passes this environment configuration into it.
- `module xray` - Invokes the reusable xray module and passes this environment configuration into it.

### `terraform/modules/acm/main.tf`

Requests and DNS-validates an ACM certificate, or reuses a supplied certificate ARN when creation is disabled.

- `resource aws_acm_certificate.this` - Create and manage the aws acm certificate resource owned by this file.
- `resource aws_route53_record.validation` - Creates the DNS record used for validation or service routing.
- `resource aws_acm_certificate_validation.this` - Waits for DNS validation before dependent services use the certificate.

### `terraform/modules/acm/outputs.tf`

Publishes reusable values produced by the acm Terraform module.

- `output certificate_arn` - Output `certificate_arn`: ACM certificate ARN used to terminate TLS.

### `terraform/modules/acm/variables.tf`

Declares the input contract for the acm Terraform module.

- `variable domain_name` - Primary CloudFront viewer domain.
- `variable subject_alternative_names` - Additional names, including the private CloudFront-to-ALB origin hostname.
- `variable hosted_zone_id` - Route 53 hosted zone used for certificate validation.
- `variable create` - Input `create`: Whether this module created a certificate rather than reusing an existing ARN.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/alb/main.tf`

Creates the internet-facing Application Load Balancer, HTTPS listener, access logging, and backend target group.

- `resource aws_lb.this` - Create and manage the aws lb resource owned by this file.
- `resource aws_lb_target_group.backend` - Defines backend health checks and the ECS destination for load-balanced requests.
- `resource aws_lb_listener.http` - Accepts HTTP or HTTPS traffic and forwards or redirects it according to the listener policy.
- `resource aws_lb_listener.https` - Accepts HTTP or HTTPS traffic and forwards or redirects it according to the listener policy.

### `terraform/modules/alb/outputs.tf`

Publishes reusable values produced by the alb Terraform module.

- `output arn` - Output `arn`: ARN of the Application Load Balancer for IAM, monitoring, and cross-module references.
- `output dns_name` - Output `dns_name`: AWS-generated ALB hostname used by Route 53 and the CloudFront origin.
- `output zone_id` - Output `zone_id`: AWS hosted-zone identifier required by an alias target.
- `output target_group_arn` - Output `target_group_arn`: Optional ALB target-group ARN used to register this ECS service.

### `terraform/modules/alb/variables.tf`

Declares the input contract for the alb Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable vpc_id` - Input `vpc_id`: ID of the VPC that owns the resource.
- `variable subnet_ids` - Input `subnet_ids`: Subnet IDs that determine the private or public network placement of the resource.
- `variable security_group_ids` - Input `security_group_ids`: Security groups attached to the workload network interface.
- `variable certificate_arn` - Input `certificate_arn`: ACM certificate ARN used to terminate TLS.
- `variable deletion_protection` - Input `deletion_protection`: Whether the managed service rejects accidental deletion.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/backup/main.tf`

Creates an encrypted AWS Backup vault, service role, schedule, retention policy, and protected-resource selection.

- `data aws_iam_policy_document.assume` - Build the trust policy that permits only the AWS Backup service to assume the backup role.
- `resource aws_iam_role.this` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy_attachment.this` - Attaches a managed IAM policy required by the role.
- `resource aws_backup_vault.this` - Creates encrypted storage for AWS Backup recovery points.
- `resource aws_backup_plan.this` - Defines backup frequency, retention, and lifecycle policy.
- `resource aws_backup_selection.this` - Selects protected resources through the backup service role and tags.

### `terraform/modules/backup/variables.tf`

Declares the input contract for the backup Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable resource_arns` - Input `resource_arns`: Protected resource ARNs selected by the AWS Backup plan.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/cloudfront/main.tf`

Creates the CloudFront distribution, origin access control, SPA routing function, WAF association, and least-privilege S3 policy.

- `data aws_iam_policy_document.bucket` - Build the S3 bucket policy that grants read access only to this CloudFront distribution and denies non-TLS requests.
- `resource aws_cloudfront_origin_access_control.this` - Create and manage the aws cloudfront origin access control resource owned by this file.
- `resource aws_cloudfront_function.spa_rewrite` - Runs lightweight request-rewrite logic at CloudFront edge locations.
- `resource aws_cloudfront_response_headers_policy.security` - Adds browser security and caching headers to CloudFront responses.
- `resource aws_cloudfront_distribution.this` - Creates the global content-delivery layer for the frontend and API origin.
- `resource aws_s3_bucket_policy.this` - Applies resource-level access controls and transport requirements to the bucket.

### `terraform/modules/cloudfront/outputs.tf`

Publishes reusable values produced by the cloudfront Terraform module.

- `output distribution_id` - Output `distribution_id`: Identifier of the distribution resource consumed by this module.
- `output domain_name` - Output `domain_name`: Fully qualified DNS name exposed by the service.
- `output hosted_zone_id` - Output `hosted_zone_id`: Route 53 hosted-zone ID in which DNS records are created.

### `terraform/modules/cloudfront/spa-rewrite.js`

Implements edge request processing used by the cloudfront Terraform module.

### `terraform/modules/cloudfront/variables.tf`

Declares the input contract for the cloudfront Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable bucket_id` - Input `bucket_id`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate. Input `bucket_id`: Identifier of the bucket resource consumed by this module.
- `variable bucket_arn` - Input `bucket_arn`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate. Input `bucket_arn`: ARN of the S3 bucket protected or consumed by the module.
- `variable bucket_domain_name` - Input `bucket_domain_name`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate. Input `bucket_domain_name`: Regional bucket hostname passed to CloudFront as its private origin.
- `variable alb_domain_name` - Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate.
- `variable use_https_origin` - Use TLS between CloudFront and the ALB.
- `variable domain_name` - Input `domain_name`: Fully qualified DNS name exposed by the service.
- `variable certificate_arn` - Input `certificate_arn`: ACM certificate ARN used to terminate TLS.
- `variable web_acl_arn` - ARN of the CLOUDFRONT-scope WAF web ACL.
- `variable price_class` - Input `price_class`: CloudFront edge-location price class used to balance reach and cost.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/cloudtrail/main.tf`

Creates an encrypted, access-logged S3 audit bucket and a multi-region CloudTrail with integrity validation.

- `locals locals` - Build partition-aware CloudTrail and account principals used by the encrypted audit-bucket policy.
- `data aws_caller_identity.current` - Read the active AWS account identity for policies, names, and ownership checks.
- `data aws_partition.current` - Read the AWS partition so service principals and ARNs work in commercial, GovCloud, or China partitions.
- `data aws_region.current` - Read the current region for KMS encryption-context restrictions and trail configuration.
- `data aws_iam_policy_document.logs` - Build the S3 bucket policy that permits CloudTrail delivery while denying insecure transport.
- `resource aws_s3_bucket.logs` - Creates an encrypted object-storage bucket for static assets, media, logs, or state.
- `resource aws_s3_bucket_ownership_controls.logs` - Makes bucket ownership deterministic and disables legacy ACL ownership ambiguity.
- `resource aws_s3_bucket_public_access_block.logs` - Prevents accidental public exposure through S3 ACLs or policies.
- `resource aws_s3_bucket_versioning.logs` - Retains prior object versions to support recovery and auditability.
- `resource aws_s3_bucket_server_side_encryption_configuration.logs` - Enforces server-side encryption for newly written objects.
- `resource aws_s3_bucket_lifecycle_configuration.logs` - Transitions or expires objects according to retention and cost policies.
- `resource aws_s3_bucket_policy.logs` - Applies resource-level access controls and transport requirements to the bucket.
- `resource aws_cloudtrail.this` - Records AWS API activity for audit, investigation, and governance.

### `terraform/modules/cloudtrail/variables.tf`

Declares the input contract for the cloudtrail Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable retention_days` - Input `retention_days`: Number of days the protected data, logs, or recovery points are retained.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/cloudwatch/main.tf`

Creates alarms, an SNS notification topic, dashboards, and operational visibility for the running service.

- `resource aws_sns_topic.alerts` - Create and manage the aws sns topic resource owned by this file.
- `resource aws_sns_topic_subscription.email` - Delivers SNS alerts to the configured recipient endpoint.
- `resource aws_cloudwatch_metric_alarm.alb_5xx` - Raises an operational alert when a service metric crosses its defined threshold.
- `resource aws_cloudwatch_metric_alarm.ecs_cpu` - Raises an operational alert when a service metric crosses its defined threshold.

### `terraform/modules/cloudwatch/variables.tf`

Declares the input contract for the cloudwatch Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable alb_arn_suffix` - Input `alb_arn_suffix`: ALB ARN suffix used by CloudWatch dimensions.
- `variable cluster_name` - Input `cluster_name`: Name of the ECS cluster used to construct service and autoscaling identifiers.
- `variable service_name` - Input `service_name`: Name of the ECS service used by deployment, autoscaling, and monitoring commands.
- `variable sns_email` - Input `sns_email`: Alarm notification email subscribed to the SNS topic.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/ecr/main.tf`

Creates immutable, encrypted container repositories with lifecycle cleanup and vulnerability scanning.

- `resource aws_ecr_repository.this` - Create and manage the aws ecr repository resource owned by this file.
- `resource aws_ecr_lifecycle_policy.this` - Removes superseded images while retaining a safe rollback window.

### `terraform/modules/ecr/outputs.tf`

Publishes reusable values produced by the ecr Terraform module.

- `output repository_urls` - Output `repository_urls`: Map of repository names to ECR push/pull URLs.
- `output repository_arns` - Output `repository_arns`: ARNs of the ECR repositories for IAM policy construction.

### `terraform/modules/ecr/variables.tf`

Declares the input contract for the ecr Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable repositories` - Input `repositories`: Repository names managed by the ECR module.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/ecs_cluster/main.tf`

Creates the ECS cluster, Container Insights settings, and encrypted ECS Exec audit logging.

- `resource aws_ecs_cluster.this` - Create and manage the aws ecs cluster resource owned by this file.
- `resource aws_cloudwatch_log_group.exec` - Stores application, task, or ECS Exec logs with controlled retention.

### `terraform/modules/ecs_cluster/outputs.tf`

Publishes reusable values produced by the ecs cluster Terraform module.

- `output cluster_arn` - Output `cluster_arn`: ARN of the ECS cluster that will run this service.
- `output cluster_name` - Output `cluster_name`: Name of the ECS cluster used to construct service and autoscaling identifiers.

### `terraform/modules/ecs_cluster/variables.tf`

Declares the input contract for the ecs cluster Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/ecs_service/main.tf`

Creates IAM roles, logs, task definitions, services, autoscaling, secrets, sidecars, and optional load-balancer integration for API or worker workloads.

- `locals locals` - Assemble least-privilege IAM statements and container-definition fragments once, then reuse them in task roles and task definitions.
- `data aws_iam_policy_document.assume` - Build the shared ECS task trust policy used by both execution and application task roles.
- `resource aws_iam_role.execution` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy_attachment.execution` - Attaches a managed IAM policy required by the role.
- `resource aws_iam_role_policy.secrets` - Attaches least-privilege inline permissions to the IAM role.
- `resource aws_iam_role.task` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy.task` - Attaches least-privilege inline permissions to the IAM role.
- `resource aws_cloudwatch_log_group.this` - Stores application, task, or ECS Exec logs with controlled retention.
- `resource aws_ecs_task_definition.this` - Defines immutable container, role, logging, health, and resource settings for a workload revision.
- `resource aws_ecs_service.this` - Keeps the requested number of application tasks running and connected to networking and load balancing.
- `resource aws_appautoscaling_target.this` - Registers the ECS service as a scalable target with capacity limits.
- `resource aws_appautoscaling_policy.cpu` - Adjusts ECS task count in response to measured utilization.

### `terraform/modules/ecs_service/outputs.tf`

Publishes reusable values produced by the ecs service Terraform module.

- `output service_name` - Output `service_name`: Name of the ECS service used by deployment, autoscaling, and monitoring commands.
- `output service_arn` - Output `service_arn`: ARN of the service resource consumed by this module.
- `output task_role_arn` - Output `task_role_arn`: ARN of the task role resource consumed by this module.
- `output task_definition_arn` - Output `task_definition_arn`: ARN of the task definition resource consumed by this module.

### `terraform/modules/ecs_service/variables.tf`

Declares the input contract for the ecs service Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable cluster_arn` - Input `cluster_arn`: ARN of the ECS cluster that will run this service.
- `variable subnet_ids` - Input `subnet_ids`: Subnet IDs that determine the private or public network placement of the resource.
- `variable security_group_ids` - Input `security_group_ids`: Security groups attached to the workload network interface.
- `variable image` - Input `image`: Container image URI and tag or digest launched by the task definition.
- `variable container_port` - Input `container_port`: TCP port on which the application container listens.
- `variable expose_port` - Input `expose_port`: Whether the ECS service should register the application port and load-balancer mapping.
- `variable cpu` - Input `cpu`: Fargate CPU units reserved by the task definition.
- `variable memory` - Input `memory`: Memory in MiB reserved by the task definition.
- `variable desired_count` - Input `desired_count`: Number of service tasks Terraform requests at steady state.
- `variable target_group_arn` - Input `target_group_arn`: Optional ALB target-group ARN used to register this ECS service.
- `variable command` - Input `command`: Optional container command that overrides the image default.
- `variable environment` - Input `environment`: Deployment environment name or the container environment-variable map, according to module context.
- `variable secrets` - Input `secrets`: Map of container environment names to Secrets Manager or Parameter Store value ARNs.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable queue_arn` - Input `queue_arn`: SQS queue ARN the task may read from or publish to.
- `variable object_storage_bucket_arn` - Input `object_storage_bucket_arn`: Optional S3 bucket ARN the task may access for private application objects.
- `variable enable_health_check` - Input `enable_health_check`: Whether the task definition includes the application container health check.
- `variable enable_autoscaling` - Input `enable_autoscaling`: Whether Application Auto Scaling resources are created for the service.
- `variable log_retention_days` - Input `log_retention_days`: Number of days CloudWatch retains logs before automatic expiration.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
- `variable ses_identity_arn` - Verified SES identity that tasks may use for outbound mail.
- `variable enable_xray` - Run the AWS X-Ray daemon sidecar and grant trace write permissions.
- `variable xray_image` - Pinned AWS X-Ray daemon container image.

### `terraform/modules/eventbridge/main.tf`

Creates the Scheduler role and recurring SQS message used to trigger campaign-expiry processing.

- `data aws_iam_policy_document.scheduler_assume` - Build the trust policy that permits only EventBridge Scheduler to assume the queue-delivery role.
- `resource aws_iam_role.scheduler` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy.scheduler` - Attaches least-privilege inline permissions to the IAM role.
- `resource aws_cloudwatch_event_bus.this` - Creates a logical event channel for future event-driven integrations.
- `resource aws_scheduler_schedule_group.this` - Groups related EventBridge Scheduler definitions for organization and lifecycle management.
- `resource aws_scheduler_schedule.campaign_expiry` - Invokes the configured target on a managed schedule without running a dedicated cron server.

### `terraform/modules/eventbridge/outputs.tf`

Publishes reusable values produced by the eventbridge Terraform module.

- `output event_bus_arn` - Output `event_bus_arn`: ARN of the event bus resource consumed by this module.
- `output schedule_arn` - Output `schedule_arn`: ARN of the schedule resource consumed by this module.

### `terraform/modules/eventbridge/variables.tf`

Declares the input contract for the eventbridge Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable queue_arn` - Input `queue_arn`: SQS queue ARN the task may read from or publish to.
- `variable dlq_arn` - Input `dlq_arn`: Dead-letter queue ARN that receives messages after retries are exhausted.
- `variable schedule_enabled` - Input `schedule_enabled`: Whether the campaign-expiry schedule is active.
- `variable schedule_expression` - Input `schedule_expression`: EventBridge Scheduler expression controlling when the campaign-expiry job runs.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/github_oidc/main.tf`

Creates GitHub OIDC trust and a least-privilege deployment role without long-lived AWS access keys.

- `locals locals` - Construct exact GitHub OIDC subject patterns for approved branches, protected environments, and optional pull requests.
- `data tls_certificate.github` - Read GitHub token-service TLS certificates so the IAM OIDC provider uses the current root thumbprint.
- `data aws_iam_policy_document.assume` - Build the web-identity trust policy that limits role assumption to the approved GitHub repository subjects.
- `resource aws_iam_openid_connect_provider.github` - Registers GitHub Actions as a federated identity provider without static AWS keys.
- `resource aws_iam_role.github` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy.github` - Attaches least-privilege inline permissions to the IAM role.

### `terraform/modules/github_oidc/outputs.tf`

Publishes reusable values produced by the github oidc Terraform module.

- `output role_arn` - Output `role_arn`: ARN of the role resource consumed by this module.

### `terraform/modules/github_oidc/variables.tf`

Declares the input contract for the github oidc Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable github_org` - Input `github_org`: GitHub organization embedded in the trusted OIDC subject patterns.
- `variable github_repo` - Input `github_repo`: GitHub repository embedded in the trusted OIDC subject patterns.
- `variable ecr_arns` - Input `ecr_arns`: ARNs of all ECR repositories controlled by the deployment role.
- `variable cluster_arn` - Input `cluster_arn`: ARN of the ECS cluster that will run this service.
- `variable allowed_branches` - Input `allowed_branches`: Branches encoded in the GitHub OIDC trust-policy subject conditions.
- `variable allowed_environments` - Input `allowed_environments`: Protected GitHub environments encoded in the OIDC trust-policy subject conditions.
- `variable allow_pull_requests` - Input `allow_pull_requests`: Whether pull-request subjects are included in the GitHub OIDC trust policy.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/guardduty/main.tf`

Enables or reuses the regional GuardDuty detector for continuous threat-intelligence findings.

- `resource aws_guardduty_detector.this` - Create and manage the aws guardduty detector resource owned by this file.

### `terraform/modules/guardduty/outputs.tf`

Publishes reusable values produced by the guardduty Terraform module.

- `output detector_id` - Output `detector_id`: Identifier of the detector resource consumed by this module.

### `terraform/modules/guardduty/variables.tf`

Declares the input contract for the guardduty Terraform module.

- `variable enabled` - Input `enabled`: Whether the optional detector, record, schedule, or resource is enabled.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/kms/main.tf`

Creates the customer-managed KMS key and policy used by application data, logs, queues, and audit services.

- `data aws_iam_policy_document.this` - Build the KMS key policy that preserves account administration and grants only required AWS services cryptographic access.
- `resource aws_kms_key.this` - ${var.name} application encryption.
- `resource aws_kms_alias.this` - Provides a stable, human-readable name for the KMS key.

### `terraform/modules/kms/outputs.tf`

Publishes reusable values produced by the kms Terraform module.

- `output key_arn` - Output `key_arn`: ARN of the key resource consumed by this module.
- `output key_id` - Output `key_id`: Identifier of the key resource consumed by this module.

### `terraform/modules/kms/variables.tf`

Declares the input contract for the kms Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable deletion_window` - Input `deletion_window`: Configured KMS recovery window before a scheduled deletion becomes permanent.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/networking/main.tf`

Builds the VPC, public/private/database subnets, routing, NAT gateways, flow logs, and required VPC endpoints.

- `locals locals` - Derive deterministic subnet CIDRs and Availability Zone mappings from the VPC range and requested AZ count.
- `data aws_availability_zones.available` - Read the currently available Availability Zones so subnet placement follows the target region.
- `data aws_region.current` - Read the active region to select the AWS-managed S3 prefix list for private endpoint routing.
- `resource aws_vpc.this` - Creates the isolated virtual network that contains all environment resources.
- `resource aws_internet_gateway.this` - Connects public subnets to the internet while private tiers remain route-controlled.
- `resource aws_subnet.public` - Creates one subnet tier across the selected Availability Zones.
- `resource aws_subnet.app` - Creates one subnet tier across the selected Availability Zones.
- `resource aws_subnet.db` - Creates one subnet tier across the selected Availability Zones.
- `resource aws_eip.nat` - Allocates stable public addresses used by NAT gateways.
- `resource aws_nat_gateway.this` - Provides outbound internet access for private application subnets without accepting inbound connections.
- `resource aws_route_table.public` - Defines how traffic leaves or moves within a subnet tier.
- `resource aws_route_table_association.public` - Attaches a route table to the intended subnet.
- `resource aws_route_table.app` - Defines how traffic leaves or moves within a subnet tier.
- `resource aws_route_table_association.app` - Attaches a route table to the intended subnet.
- `resource aws_route_table.db` - Defines how traffic leaves or moves within a subnet tier.
- `resource aws_route_table_association.db` - Attaches a route table to the intended subnet.
- `resource aws_vpc_endpoint.s3` - Keeps supported AWS service traffic on the AWS network instead of traversing the public internet.

### `terraform/modules/networking/outputs.tf`

Publishes reusable values produced by the networking Terraform module.

- `output vpc_id` - Output `vpc_id`: ID of the VPC that owns the resource.
- `output public_subnet_ids` - Output `public_subnet_ids`: Public subnet IDs used by internet-facing load-balancing or NAT resources.
- `output app_subnet_ids` - Output `app_subnet_ids`: Private application subnet IDs used by ECS workloads.
- `output db_subnet_ids` - Output `db_subnet_ids`: Private database subnet IDs used by PostgreSQL or Redis.

### `terraform/modules/networking/variables.tf`

Declares the input contract for the networking Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable cidr` - Input `cidr`: IPv4 CIDR block allocated to the VPC.
- `variable az_count` - Input `az_count`: Number of Availability Zones across which subnet tiers are created.
- `variable nat_gateway_per_az` - Input `nat_gateway_per_az`: Whether each application Availability Zone receives its own NAT gateway for resilience.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/rds_postgres/main.tf`

Provisions encrypted PostgreSQL, subnet/parameter groups, enhanced monitoring, Secrets Manager credentials, and an optional RDS Proxy.

- `data aws_iam_policy_document.monitoring_assume` - Build the trust policy that permits the RDS monitoring service to publish enhanced-monitoring metrics.
- `data aws_iam_policy_document.proxy_assume` - Build the trust policy that allows the managed RDS Proxy service to assume its Secrets Manager access role.
- `resource aws_iam_role.monitoring` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy_attachment.monitoring` - Attaches a managed IAM policy required by the role.
- `resource random_password.db` - Generates a high-entropy value without placing a human-selected password in source control.
- `resource random_password.django` - Generates a high-entropy value without placing a human-selected password in source control.
- `resource aws_secretsmanager_secret.db` - Creates a protected secret container whose value is consumed at runtime.
- `resource aws_secretsmanager_secret_version.db` - Initializes or updates the JSON value stored in Secrets Manager.
- `resource aws_db_subnet_group.this` - Restricts the database to private database subnets across Availability Zones.
- `resource aws_db_instance.this` - Creates the managed PostgreSQL database with encryption, backups, and production safety controls.
- `resource aws_iam_role.proxy` - Creates an IAM role with a narrowly defined trust relationship.
- `resource aws_iam_role_policy.proxy` - Attaches least-privilege inline permissions to the IAM role.
- `resource aws_db_proxy.this` - Pools and manages database connections between ECS tasks and PostgreSQL.
- `resource aws_db_proxy_default_target_group.this` - Defines connection-pool behavior for the database proxy.
- `resource aws_db_proxy_target.this` - Registers the PostgreSQL instance as a target behind the database proxy.
- `resource aws_secretsmanager_secret.runtime` - Creates a protected secret container whose value is consumed at runtime.
- `resource aws_secretsmanager_secret_version.runtime` - Initializes or updates the JSON value stored in Secrets Manager.

### `terraform/modules/rds_postgres/outputs.tf`

Publishes reusable values produced by the rds postgres Terraform module.

- `output endpoint` - Output `endpoint`: Direct RDS PostgreSQL writer endpoint, excluding the port.
- `output proxy_endpoint` - Output `proxy_endpoint`: RDS Proxy endpoint used by ECS tasks to pool and protect PostgreSQL connections.
- `output secret_arn` - Output `secret_arn`: ARN of the secret resource consumed by this module.
- `output db_arn` - Output `db_arn`: ARN of the db resource consumed by this module.
- `output runtime_secret_arn` - Output `runtime_secret_arn`: ARN of the runtime secret resource consumed by this module.

### `terraform/modules/rds_postgres/variables.tf`

Declares the input contract for the rds postgres Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable subnet_ids` - Input `subnet_ids`: Subnet IDs that determine the private or public network placement of the resource.
- `variable security_group_ids` - Input `security_group_ids`: Security groups attached to the workload network interface.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable engine_version` - Input `engine_version`: Requested major or minor managed-service engine version.
- `variable instance_class` - Input `instance_class`: RDS instance size controlling CPU, memory, and network capacity.
- `variable allocated_storage` - Input `allocated_storage`: Initial PostgreSQL storage allocation in GiB.
- `variable multi_az` - Input `multi_az`: Whether RDS maintains a synchronous standby in another Availability Zone.
- `variable deletion_protection` - Input `deletion_protection`: Whether the managed service rejects accidental deletion.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/redis/main.tf`

Creates an encrypted, subnet-isolated Redis replication group with mandatory Multi-AZ automatic failover.

- `resource aws_elasticache_subnet_group.this` - Create and manage the aws elasticache subnet group resource owned by this file.
- `resource aws_elasticache_replication_group.this` - Creates encrypted Redis primary and replica nodes with failover support.

### `terraform/modules/redis/outputs.tf`

Publishes reusable values produced by the redis Terraform module.

- `output endpoint` - Output `endpoint`: Primary Redis endpoint used by the application cache configuration.
- `output port` - Output `port`: Redis listener port exposed by the replication group.

### `terraform/modules/redis/variables.tf`

Declares the input contract for the redis Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable subnet_ids` - Input `subnet_ids`: Subnet IDs that determine the private or public network placement of the resource.
- `variable security_group_ids` - Input `security_group_ids`: Security groups attached to the workload network interface.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable node_type` - Input `node_type`: ElastiCache node size controlling Redis capacity and performance.
- `variable replicas` - Input `replicas`: Configured number of Redis replica nodes.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/route53/main.tf`

Creates optional IPv4/IPv6 alias records that map the application hostname to CloudFront or the ALB.

- `resource aws_route53_record.ipv4` - Create and manage the aws route53 record resource owned by this file.
- `resource aws_route53_record.ipv6` - Creates the DNS record used for validation or service routing.

### `terraform/modules/route53/outputs.tf`

Publishes reusable values produced by the route53 Terraform module.

- `output fqdn` - Output `fqdn`: Fully qualified DNS record created by the module, or null when DNS creation is disabled.

### `terraform/modules/route53/variables.tf`

Declares the input contract for the route53 Terraform module.

- `variable enabled` - Input `enabled`: Whether the optional detector, record, schedule, or resource is enabled.
- `variable zone_id` - Input `zone_id`: AWS hosted-zone identifier required by an alias target.
- `variable record_name` - Input `record_name`: Route 53 record name created by the module.
- `variable target_name` - Input `target_name`: AWS alias target name referenced by the DNS record.
- `variable target_zone_id` - Input `target_zone_id`: Identifier of the target zone resource consumed by this module.
- `variable create_ipv6` - Create an AAAA alias. Disable for IPv4-only ALB origins.

### `terraform/modules/s3_static/main.tf`

Creates the private, versioned, KMS-encrypted bucket used for frontend assets or application object storage.

- `data aws_iam_policy_document.tls` - Build the bucket policy that denies every request made without TLS.
- `resource aws_s3_bucket.this` - Create and manage the aws s3 bucket resource owned by this file.
- `resource aws_s3_bucket_ownership_controls.this` - Makes bucket ownership deterministic and disables legacy ACL ownership ambiguity.
- `resource aws_s3_bucket_public_access_block.this` - Prevents accidental public exposure through S3 ACLs or policies.
- `resource aws_s3_bucket_versioning.this` - Retains prior object versions to support recovery and auditability.
- `resource aws_s3_bucket_server_side_encryption_configuration.this` - Enforces server-side encryption for newly written objects.
- `resource aws_s3_bucket_lifecycle_configuration.this` - Transitions or expires objects according to retention and cost policies.
- `resource aws_s3_bucket_policy.tls` - Applies resource-level access controls and transport requirements to the bucket.

### `terraform/modules/s3_static/outputs.tf`

Publishes reusable values produced by the s3 static Terraform module.

- `output bucket_id` - Output `bucket_id`: Identifier of the bucket resource consumed by this module.
- `output bucket_arn` - Output `bucket_arn`: ARN of the S3 bucket protected or consumed by the module.
- `output regional_domain_name` - Output `regional_domain_name`: Regional S3 hostname used by CloudFront origin configuration.

### `terraform/modules/s3_static/variables.tf`

Declares the input contract for the s3 static Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable force_destroy` - Input `force_destroy`: Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront static origin design. Input `force_destroy`: Whether Terraform may delete the bucket while objects or versions remain.
- `variable kms_key_arn` - Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront static origin design.
- `variable create_tls_policy` - Create a standalone TLS-only bucket policy. Disable for buckets whose policy is managed by another module.
- `variable noncurrent_version_expiration_days` - Input `noncurrent_version_expiration_days`: Number of days used for noncurrent version expiration retention or timing.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/secrets_manager/main.tf`

Creates the encrypted application secret container and a stable initial secret version.

- `locals locals` - Compute reusable derived values used throughout this file.
- `resource aws_secretsmanager_secret.social` - OAuth, payment, Meta, and VibesMeet credentials.
- `resource aws_secretsmanager_secret_version.initial` - Initializes or updates the JSON value stored in Secrets Manager.

### `terraform/modules/secrets_manager/outputs.tf`

Publishes reusable values produced by the secrets manager Terraform module.

- `output secret_arn` - Output `secret_arn`: ARN of the secret resource consumed by this module.

### `terraform/modules/secrets_manager/variables.tf`

Declares the input contract for the secrets manager Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable kms_key_arn` - Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/security/main.tf`

Defines least-privilege security groups for the ALB, ECS tasks, PostgreSQL, Redis, and VPC endpoints.

- `data aws_ec2_managed_prefix_list.cloudfront` - Read AWS’s managed CloudFront origin-facing address list for restricted ALB ingress.
- `resource aws_security_group.alb` - Allow only CloudFront origin-facing traffic to the public ALB.
- `resource aws_security_group.app` - Application tasks reachable only from the ALB.
- `resource aws_security_group.db` - PostgreSQL and RDS Proxy access from application tasks.
- `resource aws_security_group.redis` - Redis access from application tasks.

### `terraform/modules/security/outputs.tf`

Publishes reusable values produced by the security Terraform module.

- `output alb_sg_id` - Output `alb_sg_id`: Identifier of the alb sg resource consumed by this module.
- `output app_sg_id` - Output `app_sg_id`: Identifier of the app sg resource consumed by this module.
- `output db_sg_id` - Output `db_sg_id`: Identifier of the db sg resource consumed by this module.
- `output redis_sg_id` - Output `redis_sg_id`: Identifier of the redis sg resource consumed by this module.

### `terraform/modules/security/variables.tf`

Declares the input contract for the security Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable vpc_id` - Input `vpc_id`: ID of the VPC that owns the resource.
- `variable app_port` - Input `app_port`: Application TCP port allowed between the ALB and ECS tasks.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/ses/main.tf`

Verifies an SES identity and publishes DKIM records required for trusted transactional email.

- `resource aws_ses_domain_identity.this` - Create and manage the aws ses domain identity resource owned by this file.
- `resource aws_route53_record.verification` - Creates the DNS record used for validation or service routing.
- `resource aws_ses_domain_dkim.this` - Generates DKIM tokens used to authenticate outgoing email.
- `resource aws_route53_record.dkim` - Creates the DNS record used for validation or service routing.

### `terraform/modules/ses/outputs.tf`

Publishes reusable values produced by the ses Terraform module.

- `output identity_arn` - Output `identity_arn`: ARN of the identity resource consumed by this module.

### `terraform/modules/ses/variables.tf`

Declares the input contract for the ses Terraform module.

- `variable domain_name` - Input `domain_name`: Fully qualified DNS name exposed by the service.
- `variable hosted_zone_id` - Input `hosted_zone_id`: Route 53 hosted-zone ID in which DNS records are created.
- `variable create_dns` - Input `create_dns`: Whether Terraform should create the dns resource or record.

### `terraform/modules/sqs/main.tf`

Creates the encrypted work queue, dead-letter queue, redrive policy, and queue access policy.

- `resource aws_sqs_queue.dlq` - Create and manage the aws sqs queue resource owned by this file.
- `resource aws_sqs_queue.tasks` - Creates a durable work queue or dead-letter queue for asynchronous processing.

### `terraform/modules/sqs/outputs.tf`

Publishes reusable values produced by the sqs Terraform module.

- `output queue_url` - Output `queue_url`: SQS queue URL consumed by the worker process.
- `output queue_arn` - Output `queue_arn`: SQS queue ARN the task may read from or publish to.
- `output dlq_arn` - Output `dlq_arn`: Dead-letter queue ARN that receives messages after retries are exhausted.

### `terraform/modules/sqs/variables.tf`

Declares the input contract for the sqs Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/waf/main.tf`

Creates a CloudFront-scoped Web ACL with AWS managed protections, IP rate limiting, logging, and metrics.

- `resource aws_wafv2_web_acl.this` - Create and manage the aws wafv2 web acl resource owned by this file.

### `terraform/modules/waf/outputs.tf`

Publishes reusable values produced by the waf Terraform module.

- `output arn` - Output `arn`: ARN of the CloudFront-scoped Web ACL attached to the distribution.
- `output id` - Output `id`: Web ACL identifier used by logging and diagnostics.

### `terraform/modules/waf/variables.tf`

Declares the input contract for the waf Terraform module.

- `variable name` - Name prefix for the web ACL.
- `variable scope` - WAF scope. CloudFront requires CLOUDFRONT and an us-east-1 provider.
- `variable rate_limit` - Maximum requests per five-minute evaluation window per source IP.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/modules/xray/main.tf`

Creates an X-Ray sampling rule so distributed traces are captured at a controlled rate.

- `resource aws_xray_sampling_rule.this` - Create and manage the aws xray sampling rule resource owned by this file.

### `terraform/modules/xray/variables.tf`

Declares the input contract for the xray Terraform module.

- `variable name` - Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.

### `terraform/outputs.tf`

Publishes deployment identifiers, endpoints, bucket names, role ARNs, and operational values from the root stack.

- `output cloudfront_url` - Output `cloudfront_url`: HTTPS URL assigned to the CloudFront distribution.
- `output application_url` - Output `application_url`: Canonical public HTTPS application URL using the configured domain.
- `output ecr_repository_urls` - Output `ecr_repository_urls`: Map of application image names to ECR URLs used by build and deployment scripts.
- `output github_actions_role_arn` - Output `github_actions_role_arn`: ARN of the github actions role resource consumed by this module.
- `output database_secret_arn` - Output `database_secret_arn`: ARN of the database secret resource consumed by this module.
- `output provider_credentials_secret_arn` - Output `provider_credentials_secret_arn`: ARN of the provider credentials secret resource consumed by this module.
- `output static_bucket_id` - Output `static_bucket_id`: Identifier of the static bucket resource consumed by this module.
- `output media_bucket_id` - Output `media_bucket_id`: Identifier of the media bucket resource consumed by this module.
- `output cloudfront_distribution_id` - Output `cloudfront_distribution_id`: CloudFront distribution ID used by deployment invalidations.
- `output ecs_cluster_arn` - Output `ecs_cluster_arn`: ARN of the ecs cluster resource consumed by this module.
- `output backend_task_definition_arn` - Output `backend_task_definition_arn`: ARN of the backend task definition resource consumed by this module.
- `output app_subnet_ids` - Output `app_subnet_ids`: Private application subnet IDs used by ECS workloads.
- `output app_security_group_id` - Output `app_security_group_id`: Security-group ID attached to the application workload.
- `output backend_service_name` - Output `backend_service_name`: ECS API service name used by deployment scripts to scale and inspect the workload.
- `output migration_task_definition_arn` - Output `migration_task_definition_arn`: ARN of the migration task definition resource consumed by this module.
- `output migration_container_name` - Output `migration_container_name`: Container name targeted by the one-off ECS database migration task.

### `terraform/providers.tf`

Configures primary and us-east-1 AWS provider aliases required by regional services such as CloudFront certificates.

- `provider aws` - Configures the provider connection and any region-specific alias used by this stack.
- `provider aws` - Configures the provider connection and any region-specific alias used by this stack.
- `data aws_caller_identity.current` - Read the active AWS account ID so names, policies, and diagnostics match the credentials running Terraform.
- `data aws_region.current` - Read the selected workload region for regional resource configuration and outputs.

### `terraform/scripts/bootstrap.sh`

Creates or verifies the remote-state bootstrap stack and writes backend configuration for a target environment.

### `terraform/scripts/deploy.sh`

Orchestrates validation, image publication, zero-capacity provisioning, database migration, service scaling, frontend publication, and cache invalidation.

### `terraform/scripts/validate.sh`

Runs formatting, initialization, validation, linting, security scanning, Go tests, and shell checks for the Terraform framework.

### `terraform/tests/framework_test.go`

Enforces repository-wide infrastructure contracts for modules, environment defaults, IAM, networking, observability, deployment order, and production safety controls.

- Function `root` - Return the Terraform framework directory used by infrastructure contract tests.
- Function `repositoryRoot` - Return the repository root so tests can compare Terraform with application, container, and workflow files.
- Function `read` - Read a fixture file and fail the current test immediately when it cannot be loaded.
- Function `TestRequiredModulesExist` - Verify that every infrastructure module required by the documented production architecture is present.
- Function `TestEnvironmentTfvarsAreComplete` - Verify that development and production variable files declare the required environment-specific settings.
- Function `TestProductionSafetyDefaults` - Verify that production defaults enable multi-AZ capacity, redundant workers, and deletion protection.
- Function `TestNoHardCodedCredentials` - Scan repository files for AWS access keys, secret-key assignments, and private-key material.
- Function `TestRemoteStateBootstrapIsIdempotent` - Verify that backend bootstrap detects existing state resources, enables S3 protections, and avoids deprecated DynamoDB locking.
- Function `TestDeploymentRunsMigrationsBeforeScalingServices` - Verify that deployment holds services at zero capacity until the one-off database migration task succeeds.
- Function `TestFrontendImageContainsProductionAssets` - Verify that the frontend image uses a build stage and serves only compiled assets from unprivileged Nginx.
- Function `TestAsyncWorkerAndSchedulerAreConnected` - Verify that the ECS worker runs the SQS processor and EventBridge Scheduler emits campaign-expiry jobs.
- Function `TestSocialAndRuntimeSecretsAreInjected` - Verify that OAuth, payment, database, and Django secrets are injected into runtime tasks rather than embedded in images.
- Function `TestTerraformFilesHaveMultilineBlocks` - Reject compressed one-line Terraform blocks that are difficult to review, document, and validate safely.
- Function `TestEdgeProtectionMatchesArchitecture` - Verify that CloudFront, WAF, ALB, and security-group relationships match the documented edge-security design.
- Function `TestTerraformRuntimeFilesAreIgnored` - Verify that local state, plans, lock artifacts, and generated Terraform runtime files cannot be committed accidentally.
- Function `TestCloudFrontOriginTLSAndSpaRouting` - Verify encrypted CloudFront-to-origin traffic and SPA fallback behavior for client-side routes.
- Function `TestRuntimeStorageAndTracingSecurity` - Verify encryption, private storage, retention, and tracing controls for runtime data and telemetry.
- Function `TestAutoscalingAndMigrationTaskDefinitions` - Verify that autoscaling policies and the dedicated migration task definition are both wired into the root stack.
- Function `TestTerraformWorkflowExecutesNativeValidation` - Verify that CI runs native Terraform formatting, initialization, and validation rather than relying only on text checks.
- Function `TestTerraformInlineObjectsHaveSeparators` - Reject malformed inline Terraform objects whose missing separators can hide configuration mistakes.
- Function `TestFrontendDefaultsToSameOriginAPI` - Verify that production browser requests default to the same-origin API path unless an explicit build-time override is supplied.
- Function `TestECSExecPermissionsMatchEnabledServiceFeature` - Verify that ECS Exec permissions are present only where the service enables the feature.
- Function `TestFrontendContainerAndComposePortsAreConsistent` - Verify that Nginx, Dockerfile, and Compose agree on the frontend container and host ports.
- Function `TestIPv4OnlyAlbOriginDoesNotPublishAAAA` - Verify that DNS does not publish an IPv6 record for an IPv4-only load-balancer origin.
- Function `TestStaticAssetDeploymentUsesSafeCacheHeaders` - Verify that hashed static assets are immutable while HTML receives revalidation-friendly cache headers.
- Function `TestDeploySupportsNonInteractiveProviderSecretInjection` - Verify that deployment can supply provider secrets non-interactively without writing them into versioned files.

### `terraform/tests/integration_test.go`

Runs native Terraform initialization and validation when the Terraform CLI is available, while cleanly skipping environments that lack it.

- Function `TestTerraformValidate` - Run terraform init without a backend and terraform validate, skipping only when the CLI is unavailable.

### `terraform/tests/scripts_test.go`

Executes bootstrap and deployment scripts in isolated fixtures to verify secure state creation, check mode, migration gating, and expected repository layout.

- Function `copyFile` - Copy a repository fixture byte-for-byte into an isolated temporary test workspace.
- Function `writeExecutable` - Write a shell fixture and apply executable permissions so it can be invoked exactly like the real script.
- Function `runCommand` - Run a command in the supplied fixture directory and capture its combined output for assertions.
- Function `prepareScriptFixture` - Create the minimal repository and mocked AWS CLI layout needed to test deployment scripts without touching real cloud resources.
- Function `TestBootstrapScriptCreatesSecureBackend` - Execute backend bootstrap against mocked AWS responses and verify versioning, encryption, public-access blocking, and lockfile configuration.
- Function `TestBootstrapCheckModeRejectsMissingState` - Verify that bootstrap check mode fails when the expected remote-state bucket or configuration is absent.
- Function `TestDeployScriptOrchestratesMigrationBeforeScaleUp` - Execute the deployment script in a fixture and verify migration success gates service scale-up and publication steps.
- Function `TestScriptFixtureContainsExpectedProjectLayout` - Verify that the isolated shell-test fixture contains every file and directory the scripts expect to reference.

### `terraform/variables.tf`

Declares configurable environment, networking, scaling, DNS, security, and integration inputs for the root stack.

- `variable project_name` - Input `project_name`: Stable project prefix used to name and tag shared AWS resources.
- `variable environment` - Input `environment`: Deployment environment name or the container environment-variable map, according to module context.
- `variable aws_region` - Input `aws_region`: AWS region in which regional workload resources are created.
- `variable domain_name` - Input `domain_name`: Fully qualified DNS name exposed by the service.
- `variable hosted_zone_id` - Input `hosted_zone_id`: Route 53 hosted-zone ID in which DNS records are created.
- `variable create_dns` - Input `create_dns`: Whether Terraform should create the dns resource or record.
- `variable vpc_cidr` - Input `vpc_cidr`: Private IPv4 CIDR allocated to the VPC; subnet CIDRs are derived from this range.
- `variable az_count` - Input `az_count`: Number of Availability Zones across which subnet tiers are created.
- `variable nat_gateway_per_az` - Input `nat_gateway_per_az`: Whether each application Availability Zone receives its own NAT gateway for resilience.
- `variable backend_image` - Input `backend_image`: ECR image URI and tag/digest launched by the API ECS task.
- `variable backend_cpu` - Input `backend_cpu`: Fargate CPU units reserved for each API task.
- `variable backend_memory` - Input `backend_memory`: Memory in MiB reserved for each API task.
- `variable backend_desired_count` - Input `backend_desired_count`: Steady-state number of API tasks requested after migrations complete.
- `variable allow_zero_capacity` - Input `allow_zero_capacity`: Permit services to start at zero tasks during staged image publication and database migration.
- `variable worker_cpu` - Input `worker_cpu`: Fargate CPU units reserved for each asynchronous worker task.
- `variable worker_memory` - Input `worker_memory`: Memory in MiB reserved for each asynchronous worker task.
- `variable worker_desired_count` - Input `worker_desired_count`: Steady-state number of SQS worker tasks requested after migrations complete.
- `variable db_instance_class` - Input `db_instance_class`: RDS PostgreSQL compute and memory class.
- `variable db_allocated_storage` - Input `db_allocated_storage`: Initial encrypted PostgreSQL storage allocation in GiB.
- `variable db_multi_az` - Input `db_multi_az`: Create a synchronous standby in another Availability Zone for production resilience.
- `variable redis_node_type` - Input `redis_node_type`: ElastiCache node class used by the Redis replication group.
- `variable redis_replicas` - Input `redis_replicas`: Number of Redis read replicas; at least one is required for Multi-AZ automatic failover.
- `variable deletion_protection` - Input `deletion_protection`: Whether the managed service rejects accidental deletion.
- `variable schedule_enabled` - Input `schedule_enabled`: Whether the campaign-expiry schedule is active.
- `variable enable_guardduty` - Input `enable_guardduty`: Whether to enable guardduty behavior.
- `variable payment_provider` - Input `payment_provider`: Backend payment adapter selected at runtime, such as fake for development or Stripe for real deposits.
- `variable cloudfront_price_class` - Input `cloudfront_price_class`: CloudFront edge-location price class controlling geographic coverage and cost.
- `variable cloudtrail_retention_days` - Input `cloudtrail_retention_days`: Number of days used for cloudtrail retention retention or timing.
- `variable github_org` - Input `github_org`: GitHub organization embedded in the trusted OIDC subject patterns.
- `variable github_repo` - Input `github_repo`: GitHub repository embedded in the trusted OIDC subject patterns.
- `variable alarm_email` - Input `alarm_email`: Email endpoint subscribed to the operational SNS alarm topic.
- `variable tags` - Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.

### `terraform/versions.tf`

Pins Terraform and provider compatibility ranges to keep deployments reproducible.

- `terraform terraform` - Define Terraform and provider compatibility before any resources are evaluated.

## Additional configuration and presentation files

### `Dockerfile.backend`

Builds the production Django/Gunicorn image with pinned Python dependencies, collected static assets, health checks, and an unprivileged runtime user.

### `Dockerfile.frontend`

Builds the React/Vite bundle in Node and serves the compiled SPA from an unprivileged Nginx runtime image.

### `docker-compose.yml`

Defines the local PostgreSQL, Django, and React/Nginx stack, including health dependencies, environment boundaries, persistent data, and developer ports.

### `frontend/nginx.conf`

Serves the compiled single-page application, falls back to index.html for client-side routes, and exposes a lightweight health endpoint.

### `frontend/src/styles.css`

Defines responsive visual layout, components, states, and accessibility details for the frontend.

### `frontend/index.html`

Defines browser metadata and the root DOM mount point used by Vite to start the React application.

### `screenshots/*.html`

Static fixtures used to generate the product screenshots included in the README and PDF. They are documentation artifacts, not production routes.

### `.env.example`, `backend/.env.example`, and `frontend/.env.example`

Safe template for local runtime configuration. Copy to .env and replace placeholders.

### `pytest.ini` and `.coveragerc`

Configures strict pytest discovery, Django settings, markers, warnings, and the default coverage/reporting command line.

### `requirements*.txt` and `security-requirements.txt`

Separate production, development, and security-tool dependencies so runtime images do not need to contain every CI scanner.

### `docs/*.dot` and `docs/*.svg`

Graphviz source files define architecture and authentication-flow diagrams; SVG files are rendered artifacts with embedded author metadata.

### `docs/schemas/*.json` and `docs/examples/*.json`

JSON Schemas define machine-verifiable VibesMeet contracts. Examples remain valid payloads and intentionally avoid extra author fields that could violate strict contract validation.

### `terraform/envs/*`

Environment value files document development and production differences. Backend examples describe remote-state locations without containing credentials.

## Safe modification rule

Change comments whenever implementation intent changes. A comment that no longer matches executable behavior is a defect and should fail review just like a broken test.
