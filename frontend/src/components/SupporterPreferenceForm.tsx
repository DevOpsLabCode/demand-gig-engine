/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Lets one authenticated supporter create or update a private campaign preference.
 */

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CalendarCheck2, MonitorPlay, TicketCheck, Users } from "lucide-react";
import type {
  AttendanceMode,
  Campaign,
  SupporterPreference,
  SupporterPreferenceInput,
} from "../types";

interface Props {
  campaign: Campaign;
  authenticated: boolean;
  onSave: (
    slug: string,
    preference: SupporterPreferenceInput,
  ) => Promise<SupporterPreference>;
}

const VOTING_STATUSES = new Set([
  "approved",
  "collecting",
  "target_reached",
  "threshold_reached",
  "feasibility_review",
  "conditionally_ready",
  "ready",
]);

function defaultInput(campaign: Campaign): SupporterPreferenceInput {
  return {
    expected_quantity: campaign.my_preference?.expected_quantity ?? 1,
    attendance_mode: campaign.my_preference?.attendance_mode ?? "physical",
    selected_date_option:
      campaign.my_preference?.selected_date_option
      ?? campaign.date_options[0]?.id
      ?? 0,
    selected_price_option:
      campaign.my_preference?.selected_price_option
      ?? campaign.price_options[0]?.id
      ?? 0,
    preferred_neighborhood:
      campaign.my_preference?.preferred_neighborhood ?? "",
    accessibility_notes:
      campaign.my_preference?.accessibility_notes ?? "",
    referral_source:
      campaign.my_preference?.referral_source
      ?? new URLSearchParams(window.location.search).get("source")
      ?? "direct",
  };
}

export function SupporterPreferenceForm({
  campaign,
  authenticated,
  onSave,
}: Props) {
  const [form, setForm] = useState<SupporterPreferenceInput>(() =>
    defaultInput(campaign),
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setForm(defaultInput(campaign));
  }, [campaign]);

  const canVote = VOTING_STATUSES.has(campaign.status);
  const hasOptions =
    campaign.date_options.length > 0 && campaign.price_options.length > 0;
  const money = useMemo(
    () =>
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: campaign.currency,
        maximumFractionDigits: 2,
      }),
    [campaign.currency],
  );

  if (!canVote) {
    return null;
  }

  if (!hasOptions) {
    return (
      <div className="review-summary">
        <strong>Voting options are not available yet.</strong>
        <p>The organizer must publish at least one proposed date and price.</p>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="review-summary">
        <strong><TicketCheck size={17} /> Sign in to vote</strong>
        <p>
          Campaign totals are public, but your date, price, quantity, and
          accessibility preferences remain attached only to your account.
        </p>
      </div>
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await onSave(campaign.slug, form);
      setMessage(
        campaign.my_preference
          ? "Your preference was updated."
          : "Your preference was recorded.",
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save preference");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel form" onSubmit={submit}>
      <div className="section-title">
        <TicketCheck size={19} />
        Your attendance preference
      </div>
      <p>
        This is a demand forecast, not a payment. You may update it while the
        campaign is accepting votes.
      </p>
      <div className="grid three">
        <label>
          <Users size={15} /> Expected tickets
          <input
            type="number"
            min="1"
            max="20"
            value={form.expected_quantity}
            onChange={(event) =>
              setForm({
                ...form,
                expected_quantity: Number(event.target.value),
              })
            }
            required
          />
        </label>
        <label>
          Attendance mode
          <select
            value={form.attendance_mode}
            onChange={(event) =>
              setForm({
                ...form,
                attendance_mode: event.target.value as AttendanceMode,
              })
            }
          >
            <option value="physical">Physical attendance</option>
            <option value="virtual">Virtual attendance</option>
          </select>
        </label>
        <label>
          <CalendarCheck2 size={15} /> Preferred date
          <select
            value={form.selected_date_option}
            onChange={(event) =>
              setForm({
                ...form,
                selected_date_option: Number(event.target.value),
              })
            }
            required
          >
            {campaign.date_options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label || new Date(option.start_datetime).toLocaleString()}
                {" — "}
                {new Date(option.start_datetime).toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <label>
          Acceptable ticket price
          <select
            value={form.selected_price_option}
            onChange={(event) =>
              setForm({
                ...form,
                selected_price_option: Number(event.target.value),
              })
            }
            required
          >
            {campaign.price_options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label || money.format(Number(option.amount))}
                {" — "}
                {money.format(Number(option.amount))}
              </option>
            ))}
          </select>
        </label>
        <label>
          Preferred neighborhood
          <input
            value={form.preferred_neighborhood ?? ""}
            onChange={(event) =>
              setForm({
                ...form,
                preferred_neighborhood: event.target.value,
              })
            }
            placeholder="Greenwich Village"
          />
        </label>
        <label>
          <MonitorPlay size={15} /> Accessibility or streaming notes
          <textarea
            value={form.accessibility_notes ?? ""}
            onChange={(event) =>
              setForm({
                ...form,
                accessibility_notes: event.target.value,
              })
            }
            rows={2}
            placeholder="Kept private; not shown in public aggregates"
          />
        </label>
      </div>
      <button className="primary" disabled={busy}>
        {busy
          ? "Saving…"
          : campaign.my_preference
            ? "Update my vote"
            : "Save my vote"}
      </button>
      {message && <p className="message">{message}</p>}
    </form>
  );
}
