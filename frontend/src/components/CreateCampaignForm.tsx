/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Collects a campaign seed together with multiple proposed dates and acceptable ticket prices.
 */

import { FormEvent, useState } from "react";
import { CalendarPlus, CircleDollarSign, Plus, Sprout, Trash2 } from "lucide-react";
import type {
  CampaignCreate,
  CampaignDateOptionInput,
  CampaignPriceOptionInput,
  GoalType,
} from "../types";

interface Props {
  onCreate: (campaign: CampaignCreate) => Promise<void>;
}

function futureLocal(days: number, hour = 19): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  value.setHours(hour, 0, 0, 0);
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 16);
}

function defaultDates(): CampaignDateOptionInput[] {
  return [45, 46, 52].map((days, index) => ({
    start_datetime: futureLocal(days),
    end_datetime: futureLocal(days, 22),
    venue_timezone: "America/New_York",
    label: ["Friday night", "Saturday night", "Following Friday"][index],
    active: true,
  }));
}

function defaultPrices(): CampaignPriceOptionInput[] {
  return [
    { amount: "35.00", currency: "USD", label: "$35 acceptable", active: true },
    { amount: "50.00", currency: "USD", label: "$50 acceptable", active: true },
    { amount: "75.00", currency: "USD", label: "$75 acceptable", active: true },
  ];
}

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
    deadline: futureLocal(30, 23),
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
    date_options: defaultDates(),
    price_options: defaultPrices(),
  });

  const set = <K extends keyof CampaignCreate>(
    key: K,
    value: CampaignCreate[K],
  ) => setForm((current) => ({ ...current, [key]: value }));

  function updateDate(
    index: number,
    key: keyof CampaignDateOptionInput,
    value: string | boolean | null,
  ) {
    set(
      "date_options",
      form.date_options.map((option, optionIndex) =>
        optionIndex === index ? { ...option, [key]: value } : option,
      ),
    );
  }

  function updatePrice(
    index: number,
    key: keyof CampaignPriceOptionInput,
    value: string | boolean,
  ) {
    set(
      "price_options",
      form.price_options.map((option, optionIndex) =>
        optionIndex === index ? { ...option, [key]: value } : option,
      ),
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (form.date_options.length === 0 || form.price_options.length === 0) {
        throw new Error("Add at least one proposed date and one ticket-price choice.");
      }
      await onCreate({
        ...form,
        deadline: new Date(form.deadline).toISOString(),
        date_options: form.date_options.map((option) => ({
          ...option,
          start_datetime: new Date(option.start_datetime).toISOString(),
          end_datetime: option.end_datetime
            ? new Date(option.end_datetime).toISOString()
            : null,
        })),
        price_options: form.price_options.map((option) => ({
          ...option,
          currency: option.currency.toUpperCase(),
        })),
      });
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

      <div className="section-title"><CalendarPlus size={19} /> Proposed dates</div>
      {form.date_options.map((option, index) => (
        <div className="grid three" key={`date-${index}`}>
          <label>Label<input value={option.label} onChange={(e) => updateDate(index, "label", e.target.value)} required /></label>
          <label>Starts<input type="datetime-local" value={option.start_datetime} onChange={(e) => updateDate(index, "start_datetime", e.target.value)} required /></label>
          <label>Ends<input type="datetime-local" value={option.end_datetime ?? ""} onChange={(e) => updateDate(index, "end_datetime", e.target.value || null)} /></label>
          <label>Venue timezone<input value={option.venue_timezone} onChange={(e) => updateDate(index, "venue_timezone", e.target.value)} required /></label>
          <button
            className="secondary"
            type="button"
            disabled={form.date_options.length === 1}
            onClick={() => set("date_options", form.date_options.filter((_, itemIndex) => itemIndex !== index))}
          >
            <Trash2 size={16} /> Remove date
          </button>
        </div>
      ))}
      <button
        className="secondary"
        type="button"
        onClick={() => set("date_options", [
          ...form.date_options,
          {
            start_datetime: futureLocal(60),
            end_datetime: futureLocal(60, 22),
            venue_timezone: "America/New_York",
            label: `Option ${form.date_options.length + 1}`,
            active: true,
          },
        ])}
      >
        <Plus size={16} /> Add proposed date
      </button>

      <div className="section-title"><CircleDollarSign size={19} /> Acceptable ticket prices</div>
      {form.price_options.map((option, index) => (
        <div className="grid three" key={`price-${index}`}>
          <label>Label<input value={option.label} onChange={(e) => updatePrice(index, "label", e.target.value)} required /></label>
          <label>Amount<input type="number" min="0" step="0.01" value={option.amount} onChange={(e) => updatePrice(index, "amount", e.target.value)} required /></label>
          <label>Currency<input maxLength={3} value={option.currency} onChange={(e) => updatePrice(index, "currency", e.target.value.toUpperCase())} required /></label>
          <button
            className="secondary"
            type="button"
            disabled={form.price_options.length === 1}
            onClick={() => set("price_options", form.price_options.filter((_, itemIndex) => itemIndex !== index))}
          >
            <Trash2 size={16} /> Remove price
          </button>
        </div>
      ))}
      <button
        className="secondary"
        type="button"
        onClick={() => set("price_options", [
          ...form.price_options,
          {
            amount: "50.00",
            currency: form.currency,
            label: `Price option ${form.price_options.length + 1}`,
            active: true,
          },
        ])}
      >
        <Plus size={16} /> Add ticket price
      </button>

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
      <button className="primary" disabled={busy}>{busy ? "Planting…" : "Plant the seed with voting options"}</button>
    </form>
  );
}
