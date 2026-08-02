/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Displays authentication state, starts OAuth login/link flows,
 * edits account type, and ends the current session.
 */

import { useEffect, useState } from "react";
import { LogIn, LogOut, RefreshCw, ShieldCheck, UserCircle2 } from "lucide-react";
import { api } from "../api";
import type { AccountType, AuthConfig, AuthProvider } from "../types";

const BACKEND_BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/api\/?$/, "");

function startProviderLogin(
  provider: AuthProvider,
  csrfToken: string,
  process: "login" | "connect" = "login",
) {
  if (!provider.enabled || !csrfToken) return;

  const form = document.createElement("form");
  form.method = "POST";

  const target = new URL(
    `${BACKEND_BASE}${provider.login_url}`,
    window.location.origin,
  );

  if (process === "connect") {
    target.searchParams.set("process", "connect");
  }

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

export function AuthPanel() {
  const [auth, setAuth] = useState<AuthConfig | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);

    try {
      const config = await api.authConfig();
      setAuth(config);
      setError("");
    } catch (err) {
      setAuth(null);
      setError(
        err instanceof Error
          ? err.message
          : "Authentication service is unavailable",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) {
    return (
      <div className="auth-panel">
        <span>Loading sign-in…</span>
      </div>
    );
  }

  if (!auth) {
    return (
      <div className="auth-panel auth-error" role="alert">
        <div className="auth-heading">
          <LogIn size={18} />
          <strong>Sign-in is temporarily unavailable</strong>
        </div>

        <span className="error">{error || "Authentication API returned an invalid response."}</span>

        <button
          className="auth-link"
          type="button"
          onClick={() => void load()}
        >
          <RefreshCw size={16} />
          Retry
        </button>
      </div>
    );
  }

  if (auth.authenticated && auth.user) {
    return (
      <div className="auth-panel authenticated">
        <div className="auth-user">
          {auth.user.avatar_url
            ? <img src={auth.user.avatar_url} alt="" />
            : <UserCircle2 />}

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
              const user = await api.updateAuthProfile({
                account_type: event.target.value as AccountType,
              });
              setAuth({ ...auth, user });
              setError("");
            } catch (err) {
              setError(
                err instanceof Error
                  ? err.message
                  : "Profile update failed",
              );
            }
          }}
        >
          {auth.account_types.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>

        <div className="linked-providers">
          <ShieldCheck size={15} />
          {auth.user.linked_providers.join(", ") || "Social account"}
        </div>

        <div className="auth-connect">
          {auth.providers
            .filter(
              (provider) =>
                provider.enabled &&
                !auth.user?.linked_providers.includes(provider.id),
            )
            .map((provider) => (
              <button
                key={provider.id}
                className="auth-link"
                type="button"
                onClick={() =>
                  startProviderLogin(
                    provider,
                    auth.csrf_token,
                    "connect",
                  )}
              >
                Link {provider.label}
              </button>
            ))}
        </div>

        {error && <span className="error">{error}</span>}

        <button
          className="auth-logout"
          type="button"
          onClick={async () => {
            try {
              await api.logout();
              await load();
            } catch (err) {
              setError(
                err instanceof Error
                  ? err.message
                  : "Sign out failed",
              );
            }
          }}
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className="auth-panel">
      <div className="auth-heading">
        <LogIn size={18} />
        <strong>Sign in to organize, support, or sponsor gigs</strong>
      </div>

      <div className="auth-providers">
        {auth.providers.map((provider) => {
          const available = provider.enabled && Boolean(auth.csrf_token);

          return (
            <button
              key={provider.id}
              className={`social-login ${provider.id}`}
              type="button"
              disabled={!available}
              title={
                available
                  ? `Continue with ${provider.label}`
                  : `${provider.label} credentials are not configured`
              }
              onClick={() =>
                startProviderLogin(provider, auth.csrf_token)
              }
            >
              {provider.label}
            </button>
          );
        })}
      </div>

      {error && <span className="error">{error}</span>}

      <small>
        OAuth credentials stay on the server. TikTok production login requires
        an approved app and HTTPS callback.
      </small>
    </div>
  );
}
