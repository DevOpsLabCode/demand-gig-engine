/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Collects a proposed gig seed, goal, deadline, organizer details, and optional Facebook community links.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { FormEvent, useState } from "react";
import { Sprout } from "lucide-react";
import type { CampaignCreate, GoalType } from "../types";

/**
 * Accept the async creation callback owned by the application shell.
 */
interface Props {
  onCreate: (campaign: CampaignCreate) => Promise<void>;
}

/**
 * Return a local datetime value thirty days ahead for the form deadline default.
 */
function inThirtyDays(): string {
  const value = new Date();
  value.setDate(value.getDate() + 30);
  return value.toISOString().slice(0, 16);
}

/**
 * Render controlled campaign fields, normalize date/currency values, and submit one validated draft to the API.
 */
export function CreateCampaignForm({ onCreate }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<CampaignCreate>({
    title: "Bring Band X to New York",
    pitch: "Commit now. The artist and venue are booked only when enough fans prove the demand.",
    artist_name: "Band X",
    city: "New York",
    country: "United States",
    proposed_date: null,
    deadline: inThirtyDays(),
    goal_type: "both",
    supporter_target: 500,
    amount_target: "25000.00",
    suggested_deposit: "25.00",
    currency: "USD",
    organizer_name: "Open Concert Community",
    organizer_email: "organizer@example.com",
    facebook_event_url: "",
    facebook_group_url: "",
    facebook_page_url: "",
  });

  const set = <K extends keyof CampaignCreate>(key: K, value: CampaignCreate[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  /** Prevent native navigation, convert the local deadline to ISO format, and preserve errors for organizer correction. */
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onCreate({ ...form, deadline: new Date(form.deadline).toISOString() });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create campaign");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel form" onSubmit={submit}>
      <div className="section-title"><Sprout size={20} /> Plant a gig seed</div>
      <div className="grid two">
        <label>Campaign title<input value={form.title} onChange={(e) => set("title", e.target.value)} required /></label>
        <label>Artist or band<input value={form.artist_name} onChange={(e) => set("artist_name", e.target.value)} required /></label>
        <label>City<input value={form.city} onChange={(e) => set("city", e.target.value)} required /></label>
        <label>Campaign deadline<input type="datetime-local" value={form.deadline} onChange={(e) => set("deadline", e.target.value)} required /></label>
      </div>
      <label>Why should this gig happen?<textarea value={form.pitch} onChange={(e) => set("pitch", e.target.value)} rows={3} required /></label>
      <div className="grid three">
        <label>Existing Facebook Event URL<input type="url" value={form.facebook_event_url ?? ""} onChange={(e) => set("facebook_event_url", e.target.value)} placeholder="https://www.facebook.com/events/..." /></label>
        <label>Primary Facebook Group URL<input type="url" value={form.facebook_group_url ?? ""} onChange={(e) => set("facebook_group_url", e.target.value)} placeholder="https://www.facebook.com/groups/..." /></label>
        <label>Facebook Page URL<input type="url" value={form.facebook_page_url ?? ""} onChange={(e) => set("facebook_page_url", e.target.value)} placeholder="https://www.facebook.com/..." /></label>
      </div>
      <div className="grid three">
        <label>Goal type
          <select value={form.goal_type} onChange={(e) => set("goal_type", e.target.value as GoalType)}>
            <option value="supporters">Supporters</option>
            <option value="money">Committed amount</option>
            <option value="both">Both</option>
          </select>
        </label>
        <label>Supporter target<input type="number" min="1" value={form.supporter_target} onChange={(e) => set("supporter_target", Number(e.target.value))} /></label>
        <label>Commitment target ($)<input type="number" min="0" step="0.01" value={form.amount_target} onChange={(e) => set("amount_target", e.target.value)} /></label>
        <label>Suggested deposit ($)<input type="number" min="0" step="0.01" value={form.suggested_deposit} onChange={(e) => set("suggested_deposit", e.target.value)} /></label>
        <label>Organizer name<input value={form.organizer_name} onChange={(e) => set("organizer_name", e.target.value)} required /></label>
        <label>Organizer email<input type="email" value={form.organizer_email} onChange={(e) => set("organizer_email", e.target.value)} required /></label>
      </div>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={busy}>{busy ? "Planting…" : "Plant the seed"}</button>
    </form>
  );
}
