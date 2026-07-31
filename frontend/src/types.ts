/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Defines shared TypeScript contracts used by React components and API functions.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

/** Select whether success is measured by attendees, committed money, or both thresholds. */
export type GoalType = "supporters" | "money" | "both";

/**
 * Represent the complete campaign API response, including owner identity, lifecycle state, calculated totals, and social links.
 */
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
  status: string;
  artist_confirmed: boolean;
  venue_confirmed: boolean;
  active_supporter_count: number;
  committed_amount: string;
  target_reached: boolean;
  progress_percent: number;
  facebook_event_url: string;
  facebook_group_url: string;
  facebook_page_url: string;
}

/**
 * Define the draft-campaign fields accepted by the creation endpoint before server-side ownership and status are assigned.
 */
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
}

/**
 * Define one supporter commitment, including the idempotency and attribution fields that make retries and marketing measurement safe.
 */
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

/**
 * Return the persisted pledge identity/status and an optional Stripe client secret for completing a deposit.
 */
export interface PledgeResult {
  pledge: { id: string; status: string };
  client_secret: string;
}

/**
 * Define the sponsor identity, contact, committed amount, and requested benefits sent to the campaign API.
 */
export interface SponsorInput {
  sponsor_name: string;
  contact_name: string;
  contact_email: string;
  amount: string;
  benefits_requested?: string;
}

/**
 * Expose only public Meta identifiers and capability flags needed by the browser; app secrets remain server-side.
 */
export interface FacebookConfig {
  enabled: boolean;
  app_id: string;
  pixel_id: string;
  graph_api_version: string;
  groups_api_available: false;
}

/**
 * Represent the normalized Facebook identity returned after the backend verifies the user token.
 */
export interface FacebookProfile {
  id: string;
  name: string;
  email: string;
  picture_url: string;
  token_expires_at?: number;
}

/**
 * Represent a managed Facebook Page and the scoped token used only for an explicit organizer publication request.
 */
export interface FacebookPage {
  id: string;
  name: string;
  category: string;
  tasks: string[];
  page_access_token: string;
  picture_url: string;
}

/**
 * Carry the attributed campaign URL and the Facebook share-dialog URL built around it.
 */
export interface FacebookShareLink {
  campaign_url: string;
  share_dialog_url: string;
}

/**
 * Describe optional VibesMeet bridge readiness and the integration capabilities implemented by this repository.
 */
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


/**
 * Enumerate marketplace roles supported by user profiles and future matching workflows.
 */
export type AccountType = "fan" | "band" | "venue" | "organizer" | "rental" | "sponsor";

/**
 * Describe one social provider, its allauth routes, and whether configuration is complete enough to enable it.
 */
export interface AuthProvider {
  id: "google" | "facebook" | "instagram" | "tiktok";
  label: string;
  icon: string;
  enabled: boolean;
  login_url: string;
  callback_path: string;
}

/**
 * Represent the editable application profile plus linked social identities for the signed-in user.
 */
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

/**
 * Return session state, provider availability, CSRF protection, and account-type choices required by the authentication panel.
 */
export interface AuthConfig {
  authenticated: boolean;
  user: AuthUser | null;
  providers: AuthProvider[];
  csrf_token: string;
  account_types: Array<{ value: AccountType; label: string }>;
}
