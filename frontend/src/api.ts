/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Provides typed browser functions for campaigns, authentication, roles, Facebook, Stripe, and VibesMeet APIs.
 */

import type {
  AuthConfig,
  AuthUser,
  Campaign,
  CampaignCreate,
  CredentialLoginInput,
  FacebookConfig,
  FacebookPage,
  FacebookProfile,
  FacebookShareLink,
  PledgeInput,
  PledgeResult,
  RoleConfig,
  RoleRequestInput,
  SponsorInput,
  UserRegistrationInput,
  UserRoleAssignment,
  VibesMeetConfig,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
let serverCsrfToken = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : Object.values(body)
            .flat()
            .filter((value): value is string => typeof value === "string")
            .join(" ");
    throw new Error(detail || `Request failed (${response.status})`);
  }
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
    request<AuthUser>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  register: (data: UserRegistrationInput) =>
    request<AuthUser>("/auth/register/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  updateAuthProfile: (data: Partial<AuthUser>) =>
    request<AuthUser>("/auth/profile/", {
      method: "PATCH",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  roleConfig: () => request<RoleConfig>("/auth/roles/"),
  requestRole: (data: RoleRequestInput) =>
    request<UserRoleAssignment>("/auth/roles/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  verifyRole: (assignmentId: number) =>
    request<UserRoleAssignment>(`/auth/roles/${assignmentId}/verify/`, {
      method: "POST",
      body: "{}",
      headers: csrfHeaders(),
    }),
  rejectRole: (assignmentId: number) =>
    request<UserRoleAssignment>(`/auth/roles/${assignmentId}/reject/`, {
      method: "POST",
      body: "{}",
      headers: csrfHeaders(),
    }),
  logout: () =>
    request<void>("/auth/logout/", {
      method: "POST",
      body: "{}",
      headers: csrfHeaders(),
    }),
  listCampaigns: () => request<Campaign[]>("/campaigns/"),
  createCampaign: (data: CampaignCreate) =>
    request<Campaign>("/campaigns/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  launchCampaign: (slug: string) =>
    request<Campaign>(`/campaigns/${slug}/launch/`, {
      method: "POST",
      body: "{}",
      headers: csrfHeaders(),
    }),
  pledge: (slug: string, data: PledgeInput) =>
    request<PledgeResult>(`/campaigns/${slug}/pledge/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  sponsor: (slug: string, data: SponsorInput) =>
    request<unknown>(`/campaigns/${slug}/sponsor/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  facebookConfig: () => request<FacebookConfig>("/facebook/config/"),
  vibesMeetConfig: () => request<VibesMeetConfig>("/vibesmeet/config/"),
  facebookLogin: (accessToken: string) =>
    request<FacebookProfile>("/facebook/login/", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
      headers: csrfHeaders(),
    }),
  facebookPages: (accessToken: string) =>
    request<FacebookPage[]>("/facebook/pages/", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
      headers: csrfHeaders(),
    }),
  facebookShareLink: (
    slug: string,
    data: { group_name?: string; referral_code?: string; source?: string },
  ) =>
    request<FacebookShareLink>(`/campaigns/${slug}/facebook/share-link/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
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
  ) =>
    request<{ post_id: string; campaign_url: string }>(
      `/campaigns/${slug}/facebook/publish-page/`,
      {
        method: "POST",
        body: JSON.stringify(data),
        headers: csrfHeaders(),
      },
    ),
};
