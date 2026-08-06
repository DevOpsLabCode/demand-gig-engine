/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Provides a comfortable, accessible card-based date, price, quantity, and attendance voting experience.
 */

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CalendarCheck2,
  Check,
  Info,
  MapPin,
  MonitorPlay,
  TicketCheck,
  Users,
} from "lucide-react";
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

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
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
    return (
      <div className="notice">
        Voting is not open in the campaign’s current lifecycle state.
      </div>
    );
  }

  if (!hasOptions) {
    return (
      <div className="notice">
        <strong>Voting options are not available yet.</strong>
        <span>The organizer must publish at least one proposed date and price.</span>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="sign-in-prompt">
        <span className="prompt-icon"><TicketCheck /></span>
        <div>
          <h4>Sign in to vote</h4>
          <p>
            Public totals remain visible. Your selection and private notes stay
            attached only to your account.
          </p>
        </div>
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
          ? "Your vote was updated."
          : "Your vote was recorded.",
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save preference");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="preference-form" onSubmit={submit}>
      <div className="preference-intro">
        <div>
          <span className="section-kicker">Your demand signal</span>
          <h4>{campaign.my_preference ? "Update your vote" : "Vote on this campaign"}</h4>
          <p>
            This is a forecast, not a payment or reservation. You can update it
            while voting remains open.
          </p>
        </div>
        {campaign.my_preference && (
          <span className="saved-indicator">
            <Check size={15} />
            Vote saved
          </span>
        )}
      </div>

      <fieldset className="choice-section">
        <legend>
          <span>1</span>
          <CalendarCheck2 size={19} />
          Choose a proposed date
        </legend>
        <div className="choice-card-grid">
          {campaign.date_options.map((option) => {
            const selected = form.selected_date_option === option.id;
            return (
              <label
                className={`choice-card ${selected ? "is-selected" : ""}`}
                key={option.id}
              >
                <input
                  type="radio"
                  name={`date-${campaign.slug}`}
                  value={option.id}
                  checked={selected}
                  onChange={() =>
                    setForm({ ...form, selected_date_option: option.id })
                  }
                />
                <span className="choice-check"><Check size={15} /></span>
                <strong>{option.label || dateLabel(option.start_datetime)}</strong>
                <span>{dateLabel(option.start_datetime)}</span>
                <small>{option.venue_timezone.replaceAll("_", " ")}</small>
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="choice-section">
        <legend>
          <span>2</span>
          <TicketCheck size={19} />
          Choose an acceptable ticket price
        </legend>
        <div className="choice-card-grid price-choices">
          {campaign.price_options.map((option) => {
            const selected = form.selected_price_option === option.id;
            return (
              <label
                className={`choice-card price-card ${selected ? "is-selected" : ""}`}
                key={option.id}
              >
                <input
                  type="radio"
                  name={`price-${campaign.slug}`}
                  value={option.id}
                  checked={selected}
                  onChange={() =>
                    setForm({ ...form, selected_price_option: option.id })
                  }
                />
                <span className="choice-check"><Check size={15} /></span>
                <strong>{money.format(Number(option.amount))}</strong>
                <span>{option.label || "Acceptable ticket price"}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="choice-section">
        <legend>
          <span>3</span>
          <Users size={19} />
          Tell us how you would attend
        </legend>
        <div className="attendance-layout">
          <div className="segmented-control" aria-label="Attendance mode">
            {([
              ["physical", "In person", MapPin],
              ["virtual", "Virtual", MonitorPlay],
            ] as [AttendanceMode, string, typeof MapPin][]).map(
              ([value, label, Icon]) => (
                <label
                  key={value}
                  className={form.attendance_mode === value ? "is-selected" : ""}
                >
                  <input
                    type="radio"
                    name={`attendance-${campaign.slug}`}
                    value={value}
                    checked={form.attendance_mode === value}
                    onChange={() =>
                      setForm({ ...form, attendance_mode: value })
                    }
                  />
                  <Icon size={18} />
                  {label}
                </label>
              ),
            )}
          </div>

          <label className="quantity-field">
            Expected tickets
            <span className="quantity-control">
              <button
                type="button"
                aria-label="Decrease expected tickets"
                onClick={() =>
                  setForm({
                    ...form,
                    expected_quantity: Math.max(1, form.expected_quantity - 1),
                  })
                }
              >
                −
              </button>
              <input
                type="number"
                min="1"
                max="20"
                inputMode="numeric"
                value={form.expected_quantity}
                onChange={(event) =>
                  setForm({
                    ...form,
                    expected_quantity: Math.max(
                      1,
                      Math.min(20, Number(event.target.value) || 1),
                    ),
                  })
                }
                aria-label="Expected ticket quantity"
                required
              />
              <button
                type="button"
                aria-label="Increase expected tickets"
                onClick={() =>
                  setForm({
                    ...form,
                    expected_quantity: Math.min(20, form.expected_quantity + 1),
                  })
                }
              >
                +
              </button>
            </span>
          </label>
        </div>
      </fieldset>

      <details className="optional-preferences">
        <summary>
          <Info size={17} />
          Add optional location or accessibility notes
        </summary>
        <div className="optional-grid">
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
              placeholder="For example, Greenwich Village"
            />
          </label>
          <label>
            Private accessibility or streaming notes
            <textarea
              value={form.accessibility_notes ?? ""}
              onChange={(event) =>
                setForm({
                  ...form,
                  accessibility_notes: event.target.value,
                })
              }
              rows={3}
              placeholder="These notes are not included in public aggregates"
            />
          </label>
        </div>
      </details>

      <div className="sticky-form-action">
        <div>
          <strong>
            {form.expected_quantity} {form.expected_quantity === 1 ? "ticket" : "tickets"}
          </strong>
          <span>
            {form.attendance_mode === "physical" ? "In person" : "Virtual"} ·{" "}
            {money.format(
              Number(
                campaign.price_options.find(
                  (option) => option.id === form.selected_price_option,
                )?.amount ?? 0,
              ),
            )} acceptable
          </span>
        </div>
        <button className="button primary" disabled={busy}>
          {busy
            ? "Saving…"
            : campaign.my_preference
              ? "Update my vote"
              : "Save my vote"}
        </button>
      </div>

      {message && (
        <p className="inline-success" role="status" aria-live="polite">
          <Check size={16} />
          {message}
        </p>
      )}
    </form>
  );
}
