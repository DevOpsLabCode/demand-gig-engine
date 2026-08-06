/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Lets users request multiple roles and lets authorized administrators verify or reject pending requests.
 */

import { BadgeCheck, Clock3, ShieldCheck, UserPlus, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { RoleConfig, RoleDefinition } from "../types";

export function RoleManager() {
  const [config, setConfig] = useState<RoleConfig | null>(null);
  const [organizationName, setOrganizationName] = useState("");
  const [busy, setBusy] = useState<string | number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      setConfig(await api.roleConfig());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role service is unavailable");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const assignmentsByCode = useMemo(
    () =>
      new Map(
        (config?.assignments ?? []).map((assignment) => [
          assignment.role.code,
          assignment,
        ]),
      ),
    [config],
  );

  async function requestRole(role: RoleDefinition) {
    setBusy(role.code);
    setError("");
    setMessage("");
    try {
      await api.requestRole({
        role_code: role.code,
        organization_name: organizationName.trim(),
      });
      setMessage(
        role.requires_verification
          ? `${role.display_name} role requested for administrator review.`
          : `${role.display_name} role added.`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role request failed");
    } finally {
      setBusy(null);
    }
  }

  async function review(id: number, decision: "verify" | "reject") {
    setBusy(id);
    setError("");
    setMessage("");
    try {
      if (decision === "verify") await api.verifyRole(id);
      else await api.rejectRole(id);
      setMessage(`Role request ${decision === "verify" ? "verified" : "rejected"}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role review failed");
    } finally {
      setBusy(null);
    }
  }

  if (!config) {
    return (
      <section className="panel" aria-live="polite">
        <strong>Loading marketplace roles…</strong>
        {error && <span className="error">{error}</span>}
      </section>
    );
  }

  return (
    <section className="panel professional-profile" aria-labelledby="role-manager-title">
      <div className="section-heading">
        <h2 id="role-manager-title">Your marketplace roles</h2>
        <p>Keep one account and request every role you actually perform.</p>
      </div>

      <label>
        Organization or professional name
        <input
          value={organizationName}
          onChange={(event) => setOrganizationName(event.target.value)}
          placeholder="Optional for professional roles"
        />
      </label>

      <div className="role-preview">
        {config.roles.map((role) => {
          const assignment = assignmentsByCode.get(role.code);
          return (
            <article key={role.code}>
              <div>
                <strong>{role.display_name}</strong>
                <span>{role.description}</span>
                {assignment && (
                  <small>
                    {assignment.verification_status === "verified" && <BadgeCheck size={14} />}
                    {assignment.verification_status === "pending" && <Clock3 size={14} />}
                    {assignment.verification_status === "rejected" && <XCircle size={14} />}
                    {assignment.verification_status}
                  </small>
                )}
              </div>
              {role.code !== "fan" && (
                <button
                  className="auth-link"
                  type="button"
                  disabled={busy === role.code || assignment?.verification_status === "verified"}
                  onClick={() => void requestRole(role)}
                >
                  <UserPlus size={15} />
                  {assignment ? "Update request" : "Request role"}
                </button>
              )}
            </article>
          );
        })}
      </div>

      {config.can_verify_roles && (
        <div className="professional-profile">
          <h3>
            <ShieldCheck size={18} /> Administrator verification queue
          </h3>
          {config.review_queue.length === 0 ? (
            <small>No pending professional-role requests.</small>
          ) : (
            config.review_queue.map((assignment) => (
              <article key={assignment.id} className="panel">
                <strong>
                  {assignment.user_display_name} — {assignment.role.display_name}
                </strong>
                <span>{assignment.organization_name || "No organization supplied"}</span>
                <div className="auth-connect">
                  <button
                    className="auth-link"
                    type="button"
                    disabled={busy === assignment.id}
                    onClick={() => void review(assignment.id, "verify")}
                  >
                    Verify
                  </button>
                  <button
                    className="auth-link"
                    type="button"
                    disabled={busy === assignment.id}
                    onClick={() => void review(assignment.id, "reject")}
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      )}

      {(message || error) && (
        <span className={error ? "error" : "message"} role={error ? "alert" : "status"}>
          {error || message}
        </span>
      )}
    </section>
  );
}
