/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Defines shared TypeScript contracts used by React components and API functions.
 */

export type GoalType = "supporters" | "money" | "both";

export type CampaignStatus =
  | "draft"
  | "pending_review"
  | "approved"
  | "collecting"
  | "target_reached"
  | "threshold_reached"
  | "confirming"
  | "feasibility_review"
  | "conditionally_ready"
  | "ready"
  | "handed_off"
  | "confirmed"
  | "live"
  | "completed"
  | "rejected"
  | "expired"
  | "failed"
  | "cancelled"
  | "canceled"
  | "not_viable"
  | "refund_pending"
  | "refunding"
  | "refunded";

export interface CampaignReviewCheck {
  key: string;
  passed: boolean;
  message: string;
}

export interface CampaignReview {
  id: number;
  decision:
    | "auto_approved"
    | "manual_review_required"
    | "manual_approved"
    | "rejected";
  reviewer_id: number | null;
  notes: string;
  checks: CampaignReviewCheck[];
  reviewed_at: string;
  previous_status: string;
  resulting_status: string;
}

export type AttendanceMode = "physical" | "virtual";

export interface CampaignDateOptionInput {
  start_datetime: string;
  end_datetime?: string | null;
  venue_timezone: string;
  label: string;
  active?: boolean;
}

export interface CampaignDateOption extends CampaignDateOptionInput {
  id: number;
  active: boolean;
}

export interface CampaignPriceOptionInput {
  amount: string;
  currency: string;
  label: string;
  active?: boolean;
}

export interface CampaignPriceOption extends CampaignPriceOptionInput {
  id: number;
  active: boolean;
}

export interface SupporterPreferenceInput {
  expected_quantity: number;
  attendance_mode: AttendanceMode;
  selected_date_option: number;
  selected_price_option: number;
  preferred_neighborhood?: string;
  accessibility_notes?: string;
  referral_source?: string;
}

export interface SupporterPreference extends SupporterPreferenceInput {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignDateResult {
  option_id: number;
  label: string;
  start_datetime: string;
  end_datetime: string | null;
  venue_timezone: string;
  supporter_count: number;
  expected_attendance: number;
  physical_expected_attendance: number;
  virtual_expected_attendance: number;
}

export interface CampaignPriceResult {
  option_id: number;
  label: string;
  amount: string;
  currency: string;
  supporter_count: number;
  expected_attendance: number;
  projected_revenue: string;
}

export interface CampaignPreferenceSummary {
  supporter_count: number;
  expected_attendance: number;
  physical_expected_attendance: number;
  virtual_expected_attendance: number;
  projected_ticket_revenue: string;
  deposits_collected: string;
  sponsor_commitments: string;
  total_conditional_funding: string;
  date_results: CampaignDateResult[];
  price_results: CampaignPriceResult[];
}

export interface Campaign {
  id: string;
  owner: {
    id: number;
    display_name: string;
    account_type: AccountType;
    avatar_url: string;
  } | null;
  title: string;
  slug: string;
  pitch: string;
  artist_name: string;
  city: string;
  country: string;
  proposed_date: string | null;
  deadline: string;
  goal_type: GoalType;
  supporter_target: number;
  amount_target: string;
  suggested_deposit: string;
  currency: string;
  status: CampaignStatus;
  artist_confirmed: boolean;
  venue_confirmed: boolean;
  organizer_name: string;
  organizer_email: string;
  active_supporter_count: number;
  committed_amount: string;
  target_reached: boolean;
  progress_percent: number;
  facebook_event_url: string;
  facebook_group_url: string;
  facebook_page_url: string;
  latest_review: CampaignReview | null;
  can_manage: boolean;
  can_review_campaign: boolean;
  date_options: CampaignDateOption[];
  price_options: CampaignPriceOption[];
  preference_summary: CampaignPreferenceSummary;
  my_preference: SupporterPreference | null;
}

export interface CampaignCreate {
  title: string;
  pitch: string;
  artist_name: string;
  city: string;
  country: string;
  proposed_date?: string | null;
  deadline: string;
  goal_type: GoalType;
  supporter_target: number;
  amount_target: string;
  suggested_deposit: string;
  currency: string;
  organizer_name: string;
  organizer_email: string;
  facebook_event_url?: string;
  facebook_group_url?: string;
  facebook_page_url?: string;
  date_options: CampaignDateOptionInput[];
  price_options: CampaignPriceOptionInput[];
}

export interface PledgeInput {
  supporter_name: string;
  supporter_email: string;
  quantity: number;
  amount: string;
  idempotency_key: string;
  source?: string;
  source_label?: string;
  referral_code?: string;
}

export interface PledgeResult {
  pledge: { id: string; status: string };
  client_secret: string;
}

export interface SponsorInput {
  sponsor_name: string;
  contact_name: string;
  contact_email: string;
  amount: string;
  benefits_requested?: string;
}

export interface FacebookConfig {
  enabled: boolean;
  app_id: string;
  pixel_id: string;
  graph_api_version: string;
  groups_api_available: false;
}

export interface FacebookProfile {
  id: string;
  name: string;
  email: string;
  picture_url: string;
  token_expires_at?: number;
}

export interface FacebookPage {
  id: string;
  name: string;
  category: string;
  tasks: string[];
  page_access_token: string;
  picture_url: string;
}

export interface FacebookShareLink {
  campaign_url: string;
  share_dialog_url: string;
}

export interface VibesMeetConfig {
  enabled: boolean;
  webhook_configured: boolean;
  base_url: string;
  contract_status: string;
  supports: {
    outbound_client: boolean;
    signed_webhook_inbox: boolean;
    external_resource_mapping: boolean;
    reservation_conversion: string;
  };
}

/** Temporary primary-profile values kept for backward compatibility. */
export type AccountType = "fan" | "band" | "venue" | "organizer" | "rental" | "sponsor";

/** Stable multiple-role codes used by the Phase 1 role API. */
export type RoleCode =
  | "fan"
  | "artist"
  | "venue"
  | "organizer"
  | "sponsor"
  | "vendor"
  | "equipment_rental"
  | "administrator";

export type RoleVerificationStatus = "pending" | "verified" | "rejected";

export interface RoleDefinition {
  code: Exclude<RoleCode, "administrator">;
  display_name: string;
  description: string;
  requires_verification: boolean;
}

export interface UserRoleAssignment {
  id: number;
  user_id: number;
  user_display_name: string;
  role: {
    code: RoleCode;
    display_name: string;
    description: string;
    requires_verification: boolean;
  };
  organization_name: string;
  profile_data: Record<string, unknown>;
  verification_status: RoleVerificationStatus;
  verified_by_id: number | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoleConfig {
  roles: RoleDefinition[];
  assignments: UserRoleAssignment[];
  can_verify_roles: boolean;
  review_queue: UserRoleAssignment[];
}

export interface RoleRequestInput {
  role_code: Exclude<RoleCode, "administrator">;
  organization_name?: string;
  profile_data?: Record<string, unknown>;
}

export interface CredentialLoginInput {
  identifier: string;
  password: string;
}

export interface UserRegistrationInput {
  display_name: string;
  email: string;
  password: string;
  password_confirm: string;
}

export interface AuthProvider {
  id: "google" | "facebook" | "instagram" | "tiktok";
  label: string;
  icon: string;
  enabled: boolean;
  login_url: string;
  callback_path: string;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  avatar_url: string;
  account_type: AccountType;
  company_name: string;
  bio: string;
  city: string;
  country: string;
  verified: boolean;
  linked_providers: string[];
}

export interface AuthConfig {
  authenticated: boolean;
  user: AuthUser | null;
  providers: AuthProvider[];
  csrf_token: string;
  password_auth_enabled: boolean;
  account_types: Array<{ value: AccountType; label: string }>;
}
