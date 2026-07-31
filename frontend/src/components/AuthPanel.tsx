/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Displays authentication state, starts OAuth login/link flows, edits account type, and ends the current session.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { useEffect, useState } from "react";
import { LogIn, LogOut, ShieldCheck, UserCircle2 } from "lucide-react";
import { api } from "../api";
import type { AccountType, AuthConfig, AuthProvider } from "../types";

/**
 * Derive the Django origin from VITE_API_BASE so allauth form posts bypass the /api prefix.
 */
const BACKEND_BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/api\/?$/, "");

/**
 * Submit a CSRF-protected form to django-allauth for either a new login or an additional account connection.
 */
function startProviderLogin(provider: AuthProvider, csrfToken: string, process: "login" | "connect" = "login") {
  // Disabled providers have missing credentials or routes, so do not navigate to a known-broken OAuth flow.
  if (!provider.enabled) return;
  const form = document.createElement("form");
  form.method = "POST";
  const target = new URL(`${BACKEND_BASE}${provider.login_url}`, window.location.origin);
  if (process === "connect") target.searchParams.set("process", "connect");
  form.action = target.toString();
  const csrf = document.createElement("input");
  csrf.type = "hidden";
  csrf.name = "csrfmiddlewaretoken";
  csrf.value = csrfToken;
  form.appendChild(csrf);
  form.style.display = "none";
  document.body.appendChild(form);
  form.submit();
}

/**
 * Render anonymous provider buttons or the authenticated profile, linked identities, account-type selector, and sign-out control.
 */
export function AuthPanel() {
  const [auth, setAuth] = useState<AuthConfig | null>(null);
  const [error, setError] = useState("");

  /** Reload authentication configuration after initial render, profile changes, linking, or logout. */
  async function load() {
    try {
      setAuth(await api.authConfig());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication unavailable");
    }
  }

  // Resolve the server session and enabled providers once the panel mounts.
  useEffect(() => { void load(); }, []);

  // Keep the layout stable while the session/provider configuration is being fetched.
  if (!auth) return <div className="auth-panel"><span>Loading sign-in…</span></div>;

  // Signed-in users see identity, role, linked providers, optional provider linking, and logout controls.
  if (auth.authenticated && auth.user) {
    return (
      <div className="auth-panel authenticated">
        <div className="auth-user">
          {auth.user.avatar_url ? <img src={auth.user.avatar_url} alt="" /> : <UserCircle2 />}
          <div>
            <strong>{auth.user.display_name}</strong>
            <span>{auth.user.email || `@${auth.user.username}`}</span>
          </div>
        </div>
        <select
          aria-label="Account type"
          value={auth.user.account_type}
          onChange={async (event) => {
            try {
              const user = await api.updateAuthProfile({ account_type: event.target.value as AccountType });
              setAuth({ ...auth, user });
            } catch (err) {
              setError(err instanceof Error ? err.message : "Profile update failed");
            }
          }}
        >
          {auth.account_types.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
        </select>
        <div className="linked-providers"><ShieldCheck size={15} /> {auth.user.linked_providers.join(", ") || "Social account"}</div>
        <div className="auth-connect">
          {auth.providers
            .filter((provider) => provider.enabled && !auth.user?.linked_providers.includes(provider.id))
            .map((provider) => (
              <button
                key={provider.id}
                className="auth-link"
                onClick={() => startProviderLogin(provider, auth.csrf_token, "connect")}
              >
                Link {provider.label}
              </button>
            ))}
        </div>
        {error && <span className="error">{error}</span>}
        <button className="auth-logout" onClick={async () => {
          try {
            await api.logout();
            await load();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Sign out failed");
          }
        }}><LogOut size={16} /> Sign out</button>
      </div>
    );
  }

  return (
    <div className="auth-panel">
      <div className="auth-heading"><LogIn size={18} /><strong>Sign in to organize, support, or sponsor gigs</strong></div>
      <div className="auth-providers">
        {auth.providers.map((provider) => (
          <button
            key={provider.id}
            className={`social-login ${provider.id}`}
            disabled={!provider.enabled}
            title={provider.enabled ? `Continue with ${provider.label}` : `${provider.label} credentials are not configured`}
            onClick={() => startProviderLogin(provider, auth.csrf_token)}
          >
            {provider.label}
          </button>
        ))}
      </div>
      {error && <span className="error">{error}</span>}
      <small>OAuth credentials stay on the server. TikTok production login requires an approved app and HTTPS callback.</small>
    </div>
  );
}
