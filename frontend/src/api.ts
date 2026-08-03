/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Provides typed browser functions for calling campaign, authentication, Facebook, Stripe, and VibesMeet API endpoints.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
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
  SponsorInput,
  UserRegistrationInput,
  VibesMeetConfig,
} from "./types";

// Use same-origin /api in production unless a local or test build explicitly supplies another backend URL.
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
// Cache the server-issued token because HttpOnly/session configurations may not expose a csrftoken cookie.
let serverCsrfToken = "";

/** Send one credentialed JSON request, normalize empty bodies, and convert non-2xx responses into Error objects. */
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

/**
 * Return the Django CSRF header from the browser cookie, falling back to the token returned by the auth configuration endpoint.
 */
function csrfHeaders(): Record<string, string> {
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
  const value = token ? decodeURIComponent(token) : serverCsrfToken;
  return value ? { "X-CSRFToken": value } : {};
}

/** Group every browser-facing backend operation behind typed methods with shared credentials, CSRF, and error handling. */
export const api = {
  // Load social-provider availability, current identity, account types, and the CSRF token used by later writes.
  authConfig: async () => {
    const config = await request<AuthConfig>("/auth/config/");
    serverCsrfToken = config.csrf_token;
    return config;
  },
  // Start a credential-backed Django session using either username or email.
  login: (data: CredentialLoginInput) =>
    request<AuthUser>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // Create a normal community-member account and automatically start its session.
  register: (data: UserRegistrationInput) =>
    request<AuthUser>("/auth/register/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // Update only the authenticated profile fields supplied by the account panel.
  updateAuthProfile: (data: Partial<AuthUser>) =>
    request<AuthUser>("/auth/profile/", {
      method: "PATCH",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // End the current server session using a CSRF-protected POST.
  logout: () =>
    request<void>("/auth/logout/", {
      method: "POST",
      body: "{}",
      headers: csrfHeaders(),
    }),
  // Read campaigns with server-calculated thresholds, status, and totals.
  listCampaigns: () => request<Campaign[]>("/campaigns/"),
  // Create a draft demand campaign owned by the authenticated organizer when signed in.
  createCampaign: (data: CampaignCreate) =>
    request<Campaign>("/campaigns/", {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // Transition a draft campaign into the collecting state through the lifecycle action endpoint.
  launchCampaign: (slug: string) =>
    request<Campaign>(`/campaigns/${slug}/launch/`, {
      method: "POST",
      body: "{}",
      headers: csrfHeaders(),
    }),
  // Create or resume an idempotent supporter pledge and receive payment data when a deposit is required.
  pledge: (slug: string, data: PledgeInput) =>
    request<PledgeResult>(`/campaigns/${slug}/pledge/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // Record a sponsor commitment that contributes to the monetary threshold.
  sponsor: (slug: string, data: SponsorInput) =>
    request<unknown>(`/campaigns/${slug}/sponsor/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // Read public Meta configuration and capability flags; secrets never leave the backend.
  facebookConfig: () => request<FacebookConfig>("/facebook/config/"),
  // Read the optional VibesMeet bridge readiness and supported-contract status.
  vibesMeetConfig: () => request<VibesMeetConfig>("/vibesmeet/config/"),
  // Ask the backend to verify a browser-obtained Facebook user token against the configured app.
  facebookLogin: (accessToken: string) =>
    request<FacebookProfile>("/facebook/login/", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
      headers: csrfHeaders(),
    }),
  // Exchange the verified user context for the Pages that organizer can manage.
  facebookPages: (accessToken: string) =>
    request<FacebookPage[]>("/facebook/pages/", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
      headers: csrfHeaders(),
    }),
  // Build a tracked campaign URL and corresponding Facebook share-dialog URL without auto-posting to Groups.
  facebookShareLink: (
    slug: string,
    data: { group_name?: string; referral_code?: string; source?: string },
  ) =>
    request<FacebookShareLink>(`/campaigns/${slug}/facebook/share-link/`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: csrfHeaders(),
    }),
  // Publish the tracked campaign message to one managed Page using its short-lived Page token.
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
