/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Provides typed browser functions for campaigns, discovery, profile media, authentication, roles, Facebook, Stripe, and VibesMeet APIs.
 */

import type {
  AuthConfig,
  AuthUser,
  Campaign,
  CampaignCreate,
  CampaignDateOption,
  CampaignDateOptionInput,
  CampaignPreferenceSummary,
  CampaignPriceOption,
  CampaignPriceOptionInput,
  CredentialLoginInput,
  DiscoveryProfile,
  FacebookConfig,
  FacebookPage,
  FacebookProfile,
  FacebookShareLink,
  PledgeInput,
  PledgeResult,
  ProfileMedia,
  ProfileMediaType,
  RoleConfig,
  RoleRequestInput,
  SponsorInput,
  SupporterPreference,
  SupporterPreferenceInput,
  UserRegistrationInput,
  UserRoleAssignment,
  VibesMeetConfig,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
let serverCsrfToken = "";

async function responseBody(response: Response) {
  return response.json().catch(() => ({}));
}

function errorFromResponse(response: Response, body: Record<string, unknown>): Error {
  const detail =
    typeof body.detail === "string"
      ? body.detail
      : Object.values(body)
          .flat()
          .filter((value): value is string => typeof value === "string")
          .join(" ");
  if (response.status >= 500 && detail) {
    return new Error(`Request failed (${response.status}): ${detail}`);
  }
  return new Error(detail || `Request failed (${response.status})`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = (await responseBody(response)) as Record<string, unknown>;
  if (!response.ok) throw errorFromResponse(response, body);
  return body as T;
}

async function requestForm<T>(path: string, form: FormData, method = "POST"): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "include",
    body: form,
    headers: csrfHeaders(),
  });
  const body = (await responseBody(response)) as Record<string, unknown>;
  if (!response.ok) throw errorFromResponse(response, body);
  return body as T;
}

function csrfHeaders(): Record<string, string> {
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
  const value = token ? decodeURIComponent(token) : serverCsrfToken;
  return value ? { "X-CSRFToken": value } : {};
}

export const api = {
  authConfig: async () => {
    const config = await request<AuthConfig>("/auth/config/");
    serverCsrfToken = config.csrf_token;
    return config;
  },
  login: (data: CredentialLoginInput) =>
    request<AuthUser>("/auth/login/", { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  register: (data: UserRegistrationInput) =>
    request<AuthUser>("/auth/register/", { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  updateAuthProfile: (data: Partial<AuthUser>) =>
    request<AuthUser>("/auth/profile/", { method: "PATCH", body: JSON.stringify(data), headers: csrfHeaders() }),
  discoveryProfile: () => request<DiscoveryProfile>("/auth/discovery-profile/"),
  updateDiscoveryProfile: (data: Partial<Pick<DiscoveryProfile, "state" | "preferred_cities">>) =>
    request<DiscoveryProfile>("/auth/discovery-profile/", { method: "PATCH", body: JSON.stringify(data), headers: csrfHeaders() }),
  resendEmailVerification: () =>
    request<{ detail: string; email_verified: boolean }>("/auth/email/resend-verification/", { method: "POST", body: "{}", headers: csrfHeaders() }),
  listProfileMedia: () => request<ProfileMedia[]>("/auth/profile/media/"),
  uploadProfileMedia: (file: File, mediaType: ProfileMediaType, caption = "") => {
    const form = new FormData();
    form.append("file", file);
    form.append("media_type", mediaType);
    form.append("caption", caption);
    return requestForm<ProfileMedia>("/auth/profile/media/", form);
  },
  deleteProfileMedia: (mediaId: string) =>
    request<void>(`/auth/profile/media/${mediaId}/`, { method: "DELETE", headers: csrfHeaders() }),
  roleConfig: () => request<RoleConfig>("/auth/roles/"),
  requestRole: (data: RoleRequestInput) =>
    request<UserRoleAssignment>("/auth/roles/", { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  verifyRole: (assignmentId: number) =>
    request<UserRoleAssignment>(`/auth/roles/${assignmentId}/verify/`, { method: "POST", body: "{}", headers: csrfHeaders() }),
  rejectRole: (assignmentId: number) =>
    request<UserRoleAssignment>(`/auth/roles/${assignmentId}/reject/`, { method: "POST", body: "{}", headers: csrfHeaders() }),
  logout: () => request<void>("/auth/logout/", { method: "POST", body: "{}", headers: csrfHeaders() }),
  listCampaigns: () => request<Campaign[]>("/campaigns/"),
  listCampaignReviewQueue: () => request<Campaign[]>("/campaigns/review-queue/"),
  createCampaign: (data: CampaignCreate) =>
    request<Campaign>("/campaigns/", { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  updateCampaign: (slug: string, data: Partial<CampaignCreate>) =>
    request<Campaign>(`/campaigns/${slug}/`, { method: "PATCH", body: JSON.stringify(data), headers: csrfHeaders() }),
  submitCampaignForReview: (slug: string) =>
    request<Campaign>(`/campaigns/${slug}/submit-review/`, { method: "POST", body: "{}", headers: csrfHeaders() }),
  approveCampaign: (slug: string, notes: string) =>
    request<Campaign>(`/campaigns/${slug}/approve/`, { method: "POST", body: JSON.stringify({ notes }), headers: csrfHeaders() }),
  rejectCampaign: (slug: string, notes: string) =>
    request<Campaign>(`/campaigns/${slug}/reject/`, { method: "POST", body: JSON.stringify({ notes }), headers: csrfHeaders() }),
  launchCampaign: (slug: string) =>
    request<Campaign>(`/campaigns/${slug}/launch/`, { method: "POST", body: "{}", headers: csrfHeaders() }),
  listDateOptions: (slug: string) => request<CampaignDateOption[]>(`/campaigns/${slug}/date-options/`),
  createDateOption: (slug: string, data: CampaignDateOptionInput) =>
    request<CampaignDateOption>(`/campaigns/${slug}/date-options/`, { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  updateDateOption: (slug: string, optionId: number, data: Partial<CampaignDateOptionInput>) =>
    request<CampaignDateOption>(`/campaigns/${slug}/date-options/${optionId}/`, { method: "PATCH", body: JSON.stringify(data), headers: csrfHeaders() }),
  deleteDateOption: (slug: string, optionId: number) =>
    request<void>(`/campaigns/${slug}/date-options/${optionId}/`, { method: "DELETE", headers: csrfHeaders() }),
  listPriceOptions: (slug: string) => request<CampaignPriceOption[]>(`/campaigns/${slug}/price-options/`),
  createPriceOption: (slug: string, data: CampaignPriceOptionInput) =>
    request<CampaignPriceOption>(`/campaigns/${slug}/price-options/`, { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  updatePriceOption: (slug: string, optionId: number, data: Partial<CampaignPriceOptionInput>) =>
    request<CampaignPriceOption>(`/campaigns/${slug}/price-options/${optionId}/`, { method: "PATCH", body: JSON.stringify(data), headers: csrfHeaders() }),
  deletePriceOption: (slug: string, optionId: number) =>
    request<void>(`/campaigns/${slug}/price-options/${optionId}/`, { method: "DELETE", headers: csrfHeaders() }),
  getPreferenceSummary: (slug: string) => request<CampaignPreferenceSummary>(`/campaigns/${slug}/preference-summary/`),
  getMyPreference: (slug: string) => request<{ preference: SupporterPreference | null }>(`/campaigns/${slug}/preference/`),
  savePreference: (slug: string, data: SupporterPreferenceInput) =>
    request<SupporterPreference>(`/campaigns/${slug}/preference/`, { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  pledge: (slug: string, data: PledgeInput) =>
    request<PledgeResult>(`/campaigns/${slug}/pledge/`, { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  sponsor: (slug: string, data: SponsorInput) =>
    request<unknown>(`/campaigns/${slug}/sponsor/`, { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  facebookConfig: () => request<FacebookConfig>("/facebook/config/"),
  vibesMeetConfig: () => request<VibesMeetConfig>("/vibesmeet/config/"),
  facebookLogin: (accessToken: string) =>
    request<FacebookProfile>("/facebook/login/", { method: "POST", body: JSON.stringify({ access_token: accessToken }), headers: csrfHeaders() }),
  facebookPages: (accessToken: string) =>
    request<FacebookPage[]>("/facebook/pages/", { method: "POST", body: JSON.stringify({ access_token: accessToken }), headers: csrfHeaders() }),
  facebookShareLink: (slug: string, data: { group_name?: string; referral_code?: string; source?: string }) =>
    request<FacebookShareLink>(`/campaigns/${slug}/facebook/share-link/`, { method: "POST", body: JSON.stringify(data), headers: csrfHeaders() }),
  publishFacebookPage: (
    slug: string,
    data: { page_id: string; page_access_token: string; message?: string; group_name?: string; referral_code?: string; source?: string },
  ) =>
    request<{ post_id: string; campaign_url: string }>(`/campaigns/${slug}/facebook/publish-page/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
};
