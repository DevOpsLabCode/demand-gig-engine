import type {
  Campaign,
  CampaignCreate,
  FacebookConfig,
  FacebookPage,
  FacebookProfile,
  FacebookShareLink,
  PledgeInput,
  PledgeResult,
  SponsorInput,
  VibesMeetConfig,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return body as T;
}

export const api = {
  listCampaigns: () => request<Campaign[]>("/campaigns/"),
  createCampaign: (data: CampaignCreate) =>
    request<Campaign>("/campaigns/", { method: "POST", body: JSON.stringify(data) }),
  launchCampaign: (slug: string) =>
    request<Campaign>(`/campaigns/${slug}/launch/`, { method: "POST", body: "{}" }),
  pledge: (slug: string, data: PledgeInput) =>
    request<PledgeResult>(`/campaigns/${slug}/pledge/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  sponsor: (slug: string, data: SponsorInput) =>
    request<unknown>(`/campaigns/${slug}/sponsor/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  facebookConfig: () => request<FacebookConfig>("/facebook/config/"),
  vibesMeetConfig: () => request<VibesMeetConfig>("/vibesmeet/config/"),
  facebookLogin: (accessToken: string) =>
    request<FacebookProfile>("/facebook/login/", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
    }),
  facebookPages: (accessToken: string) =>
    request<FacebookPage[]>("/facebook/pages/", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
    }),
  facebookShareLink: (slug: string, data: { group_name?: string; referral_code?: string; source?: string }) =>
    request<FacebookShareLink>(`/campaigns/${slug}/facebook/share-link/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  publishFacebookPage: (
    slug: string,
    data: {
      page_id: string;
      page_access_token: string;
      message?: string;
      group_name?: string;
      referral_code?: string;
      source?: string;
    },
  ) => request<{ post_id: string; campaign_url: string }>(`/campaigns/${slug}/facebook/publish-page/`, {
    method: "POST",
    body: JSON.stringify(data),
  }),
};
