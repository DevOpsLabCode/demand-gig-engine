/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Presents stable credential/social authentication, registration, verification feedback, and account controls.
 */

import {
  BadgeCheck,
  Building2,
  Eye,
  EyeOff,
  KeyRound,
  LogIn,
  LogOut,
  Mail,
  Music2,
  PackageCheck,
  RefreshCw,
  ShieldCheck,
  Store,
  UserCircle2,
  UserPlus,
  Users,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { AccountType, AuthConfig, AuthProvider } from "../types";

const BACKEND_BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/api\/?$/, "");

export type AuthState = "loading" | "anonymous" | "authenticated";

interface AuthPanelProps {
  onAuthStateChange?: (state: AuthState) => void;
}

const PROVIDER_MARKS: Record<AuthProvider["id"], string> = {
  google: "G",
  facebook: "f",
  instagram: "◎",
  tiktok: "♪",
};

function startProviderLogin(
  provider: AuthProvider,
  csrfToken: string,
  process: "login" | "connect" = "login",
) {
  if (!provider.enabled || !csrfToken || !provider.login_url) return;

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

function accountTypeLabel(value: AccountType, fallback: string): string {
  if (value === "fan") return "Community member";
  if (value === "band") return "Artist / band";
  if (value === "rental") return "Equipment vendor / rental";
  return fallback;
}

export function AuthPanel({ onAuthStateChange }: AuthPanelProps) {
  const [auth, setAuth] = useState<AuthConfig | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [identifier, setIdentifier] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    onAuthStateChange?.("loading");
    try {
      const config = await api.authConfig();
      setAuth(config);
      setError("");
      onAuthStateChange?.(config.authenticated ? "authenticated" : "anonymous");
    } catch (err) {
      setAuth(null);
      setError(err instanceof Error ? err.message : "Authentication service is unavailable");
      onAuthStateChange?.("anonymous");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function acceptAuthenticatedUser(user: NonNullable<AuthConfig["user"]>) {
    setAuth((current) => current ? { ...current, authenticated: true, user } : current);
    onAuthStateChange?.("authenticated");
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const user = await api.login({ identifier: identifier.trim(), password });
      setPassword("");
      acceptAuthenticatedUser(user);
      setMessage("Signed in successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      setSubmitting(false);
      return;
    }

    try {
      const user = await api.register({
        display_name: displayName.trim(),
        email: email.trim(),
        password,
        password_confirm: passwordConfirm,
      });
      setIdentifier(email.trim());
      setPassword("");
      setPasswordConfirm("");
      acceptAuthenticatedUser(user);
      setMessage(
        user.verification_sent === false
          ? "Account created, but the verification email could not be delivered. Open Profile and use Resend email."
          : "Account created. Check your inbox and spam folder for the verification link.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section className="auth-loading-card" aria-live="polite">
        <div className="auth-loading-mark"><Music2 /></div>
        <strong>Opening Open Concert Network…</strong>
        <span>Checking your secure session.</span>
      </section>
    );
  }

  if (!auth) {
    return (
      <section className="auth-service-error" role="alert">
        <div className="auth-heading"><LogIn size={20} /><strong>Sign-in is temporarily unavailable</strong></div>
        <span className="error">{error || "Authentication API returned an invalid response."}</span>
        <button className="auth-link" type="button" onClick={() => void load()}><RefreshCw size={16} /> Retry</button>
      </section>
    );
  }

  if (auth.authenticated && auth.user) {
    return (
      <section className="auth-panel authenticated">
        <div className="auth-user">
          {auth.user.avatar_url ? <img src={auth.user.avatar_url} alt="" /> : <UserCircle2 />}
          <div>
            <span className="member-status"><BadgeCheck size={14} /> User account</span>
            <strong>{auth.user.display_name}</strong>
            <span>{auth.user.email || `@${auth.user.username}`}</span>
          </div>
        </div>

        <div className="professional-profile">
          <label htmlFor="account-type">
            Active profile
            <select
              id="account-type"
              value={auth.user.account_type}
              onChange={async (event) => {
                try {
                  const user = await api.updateAuthProfile({ account_type: event.target.value as AccountType });
                  setAuth({ ...auth, user });
                  setError("");
                  setMessage(`${accountTypeLabel(user.account_type, user.account_type)} profile active.`);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Profile update failed");
                }
              }}
            >
              {auth.account_types.map((type) => (
                <option key={type.value} value={type.value}>{accountTypeLabel(type.value, type.label)}</option>
              ))}
            </select>
          </label>
          <small>One login can represent you as a fan, artist/band, venue, organizer, sponsor, or equipment provider.</small>
        </div>

        <div className="linked-providers">
          <ShieldCheck size={15} />
          {auth.user.linked_providers.join(", ") || "Password-protected account"}
        </div>

        <div className="auth-connect">
          {auth.providers
            .filter((provider) => provider.enabled && !auth.user?.linked_providers.includes(provider.id))
            .map((provider) => (
              <button
                key={provider.id}
                className={`auth-link provider-link ${provider.id}`}
                type="button"
                onClick={() => startProviderLogin(provider, auth.csrf_token, "connect")}
              >
                <span className="provider-mark">{PROVIDER_MARKS[provider.id]}</span>
                Link {provider.label}
              </button>
            ))}
        </div>

        {(error || message) && <span className={error ? "error" : "message"}>{error || message}</span>}

        <button
          className="auth-logout"
          type="button"
          onClick={async () => {
            try {
              await api.logout();
              setMessage("");
              setMode("login");
              await load();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Sign out failed");
            }
          }}
        >
          <LogOut size={16} /> Sign out
        </button>
      </section>
    );
  }

  return (
    <section className="auth-gateway">
      <div className="auth-story">
        <span className="network-kicker"><Music2 size={17} /> Open Concert Network</span>
        <h1>One account.<br />Every way to make live music happen.</h1>
        <p>Discover shows as a fan, then activate a richer profile when you are an artist, band, venue, organizer, sponsor, or equipment provider.</p>

        <div className="role-preview">
          <article><Users /><div><strong>Community member</strong><span>Discover, support, reserve, and share gigs.</span></div></article>
          <article><Building2 /><div><strong>Venue</strong><span>Show your room, capacity, media, and respond to proven demand.</span></div></article>
          <article><PackageCheck /><div><strong>Artist / vendor</strong><span>Publish media, social links, videos, services, and availability.</span></div></article>
          <article><Store /><div><strong>Open marketplace</strong><span>Match fans, bands, venues, vendors, organizers, and sponsors.</span></div></article>
        </div>

        <div className="auth-trust-row">
          <span><ShieldCheck size={16} /> Secure server session</span>
          <span><BadgeCheck size={16} /> Verified identity path</span>
        </div>
      </div>

      <div className="auth-card">
        <div className="auth-card-header">
          <span className="auth-card-icon">{mode === "login" ? <KeyRound /> : <UserPlus />}</span>
          <div>
            <span>{mode === "login" ? "Welcome back" : "Join the network"}</span>
            <h2>{mode === "login" ? "Sign in to continue" : "Create your user account"}</h2>
          </div>
        </div>

        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={mode === "login" ? "active" : ""}
            onClick={() => { setMode("login"); setError(""); setMessage(""); }}
          >Sign in</button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={mode === "register" ? "active" : ""}
            onClick={() => { setMode("register"); setError(""); setMessage(""); }}
          >Create account</button>
        </div>

        {mode === "login" ? (
          <form className="credential-form" onSubmit={submitLogin}>
            <label>Email or username
              <span className="input-with-icon"><Mail size={18} />
                <input type="text" autoComplete="username" required value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="you@example.com" />
              </span>
            </label>
            <label>Password
              <span className="input-with-icon password-input"><KeyRound size={18} />
                <input type={showPassword ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" />
                <button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((current) => !current)}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>
            <button className="auth-submit" type="submit" disabled={submitting}><LogIn size={18} /> {submitting ? "Signing in…" : "Sign in"}</button>
          </form>
        ) : (
          <form className="credential-form" onSubmit={submitRegistration}>
            <label>Your name
              <span className="input-with-icon"><UserCircle2 size={18} />
                <input type="text" autoComplete="name" required value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="How the community will know you" />
              </span>
            </label>
            <label>Email
              <span className="input-with-icon"><Mail size={18} />
                <input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
              </span>
            </label>
            <label>Password
              <span className="input-with-icon password-input"><KeyRound size={18} />
                <input type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" />
                <button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((current) => !current)}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>
            <label>Confirm password
              <span className="input-with-icon"><KeyRound size={18} />
                <input type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} required value={passwordConfirm} onChange={(event) => setPasswordConfirm(event.target.value)} placeholder="Repeat your password" />
              </span>
            </label>
            <button className="auth-submit" type="submit" disabled={submitting}><UserPlus size={18} /> {submitting ? "Creating account…" : "Create free account"}</button>
          </form>
        )}

        {(error || message) && (
          <div className={`auth-feedback ${error ? "error" : "message"}`} role={error ? "alert" : "status"}>{error || message}</div>
        )}

        <div className="auth-divider"><span>or continue with</span></div>
        <div className="auth-providers">
          {auth.providers.map((provider) => {
            const available = provider.enabled && Boolean(auth.csrf_token) && Boolean(provider.login_url);
            return (
              <button
                key={provider.id}
                className={`social-login ${provider.id}`}
                type="button"
                disabled={!available}
                title={available ? `Continue with ${provider.label}` : `${provider.label} login is not configured yet`}
                onClick={() => startProviderLogin(provider, auth.csrf_token)}
              >
                <span className="provider-mark">{PROVIDER_MARKS[provider.id]}</span>
                <span>{provider.label}</span>
              </button>
            );
          })}
        </div>

        <small className="registration-note">Email verification is required before trust-sensitive Stage 2 actions. Professional roles can be activated from your profile after sign-in.</small>
      </div>
    </section>
  );
}
