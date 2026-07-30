export type GoalType = "supporters" | "money" | "both";

export interface Campaign {
  id: string;
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
