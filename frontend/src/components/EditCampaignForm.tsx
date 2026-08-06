/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Lets a campaign owner edit the full seed at any lifecycle stage without exposing protected state fields.
 */

import { FormEvent, useMemo, useState } from "react";
import {
  CalendarPlus,
  Check,
  CircleDollarSign,
  Info,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { api } from "../api";
import type {
  Campaign,
  CampaignCreate,
  CampaignDateOptionInput,
  CampaignPriceOptionInput,
  GoalType,
} from "../types";

interface Props {
  campaign: Campaign;
  onSaved: () => Promise<void> | void;
  onCancel: () => void;
}

interface EditableDate extends CampaignDateOptionInput {
  id?: number;
  local_key: string;
}

interface EditablePrice extends CampaignPriceOptionInput {
  id?: number;
  local_key: string;
}

function toLocalInput(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function toIso(value: string | null | undefined): string | null {
  return value ? new Date(value).toISOString() : null;
}

export function EditCampaignForm({ campaign, onSaved, onCancel }: Props) {
  const [form, setForm] = useState({
    title: campaign.title,
    pitch: campaign.pitch,
    artist_name: campaign.artist_name,
    city: campaign.city,
    country: campaign.country,
    deadline: toLocalInput(campaign.deadline),
    goal_type: campaign.goal_type,
    supporter_target: campaign.supporter_target,
    amount_target: campaign.amount_target,
    suggested_deposit: campaign.suggested_deposit,
    currency: campaign.currency,
    organizer_name: campaign.organizer_name,
    organizer_email: campaign.organizer_email,
    facebook_event_url: campaign.facebook_event_url ?? "",
    facebook_group_url: campaign.facebook_group_url ?? "",
    facebook_page_url: campaign.facebook_page_url ?? "",
  });
  const [dates, setDates] = useState<EditableDate[]>(
    campaign.date_options.map((option) => ({
      ...option,
      start_datetime: toLocalInput(option.start_datetime),
      end_datetime: toLocalInput(option.end_datetime),
      local_key: `date-${option.id}`,
    })),
  );
  const [prices, setPrices] = useState<EditablePrice[]>(
    campaign.price_options.map((option) => ({
      ...option,
      local_key: `price-${option.id}`,
    })),
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const votedDateIds = useMemo(
    () =>
      new Set(
        campaign.preference_summary.date_results
          .filter((result) => result.supporter_count > 0)
          .map((result) => result.option_id),
      ),
    [campaign.preference_summary.date_results],
  );
  const votedPriceIds = useMemo(
    () =>
      new Set(
        campaign.preference_summary.price_results
          .filter((result) => result.supporter_count > 0)
          .map((result) => result.option_id),
      ),
    [campaign.preference_summary.price_results],
  );

  function updateDate(
    key: string,
    field: keyof CampaignDateOptionInput,
    value: string | boolean | null,
  ) {
    setDates((current) =>
      current.map((option) =>
        option.local_key === key ? { ...option, [field]: value } : option,
      ),
    );
  }

  function updatePrice(
    key: string,
    field: keyof CampaignPriceOptionInput,
    value: string | boolean,
  ) {
    setPrices((current) =>
      current.map((option) =>
        option.local_key === key ? { ...option, [field]: value } : option,
      ),
    );
  }

  function removeDate(option: EditableDate) {
    if (option.id && votedDateIds.has(option.id)) {
      setError(
        "This date already has supporter votes. Edit it or add another date instead of removing it.",
      );
      return;
    }
    if (dates.length === 1) {
      setError("A campaign seed must keep at least one proposed date.");
      return;
    }
    setError("");
    setDates((current) =>
      current.filter((item) => item.local_key !== option.local_key),
    );
  }

  function removePrice(option: EditablePrice) {
    if (option.id && votedPriceIds.has(option.id)) {
      setError(
        "This price already has supporter votes. Edit it or add another price instead of removing it.",
      );
      return;
    }
    if (prices.length === 1) {
      setError("A campaign seed must keep at least one ticket-price choice.");
      return;
    }
    setError("");
    setPrices((current) =>
      current.filter((item) => item.local_key !== option.local_key),
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const payload: Partial<CampaignCreate> & {
        date_options: Array<CampaignDateOptionInput & { id?: number }>;
        price_options: Array<CampaignPriceOptionInput & { id?: number }>;
      } = {
        ...form,
        deadline: new Date(form.deadline).toISOString(),
        currency: form.currency.toUpperCase(),
        date_options: dates.map(({ local_key: _localKey, ...option }) => ({
          ...option,
          start_datetime: new Date(option.start_datetime).toISOString(),
          end_datetime: toIso(option.end_datetime),
        })),
        price_options: prices.map(({ local_key: _localKey, ...option }) => ({
          ...option,
          currency: option.currency.toUpperCase(),
        })),
      };

      await api.updateCampaign(campaign.slug, payload);
      setMessage("Campaign seed updated and recorded in the audit history.");
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Campaign update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="owner-edit-form" onSubmit={submit}>
      <div className="owner-edit-banner">
        <ShieldCheck />
        <div>
          <strong>Editable at every campaign stage</strong>
          <p>
            The owner may update the seed without changing ownership, slug,
            lifecycle status, confirmations, payments, reviews, or supporter records.
          </p>
        </div>
      </div>

      <section className="owner-edit-section">
        <div className="subsection-heading">
          <Info />
          <div>
            <strong>Campaign story and location</strong>
            <span>Keep the public seed accurate as planning develops.</span>
          </div>
        </div>
        <div className="comfortable-form two-column">
          <label className="full-width">
            Campaign title
            <input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              required
            />
          </label>
          <label>
            Artist or band
            <input
              value={form.artist_name}
              onChange={(event) =>
                setForm({ ...form, artist_name: event.target.value })
              }
              required
            />
          </label>
          <label>
            City
            <input
              value={form.city}
              onChange={(event) => setForm({ ...form, city: event.target.value })}
              required
            />
          </label>
          <label>
            Country
            <input
              value={form.country}
              onChange={(event) =>
                setForm({ ...form, country: event.target.value })
              }
              required
            />
          </label>
          <label className="full-width">
            Campaign pitch
            <textarea
              rows={5}
              value={form.pitch}
              onChange={(event) => setForm({ ...form, pitch: event.target.value })}
              required
            />
          </label>
        </div>
      </section>

      <section className="owner-edit-section">
        <div className="subsection-heading">
          <CalendarPlus />
          <div>
            <strong>Dates and acceptable prices</strong>
            <span>Voted choices may be edited but cannot be removed.</span>
          </div>
        </div>

        <div className="owner-option-heading">
          <strong>Proposed dates</strong>
          <button
            className="button secondary compact"
            type="button"
            onClick={() =>
              setDates((current) => [
                ...current,
                {
                  local_key: crypto.randomUUID(),
                  start_datetime: "",
                  end_datetime: null,
                  venue_timezone: "America/New_York",
                  label: `Date option ${current.length + 1}`,
                  active: true,
                },
              ])
            }
          >
            <Plus size={16} /> Add date
          </button>
        </div>

        <div className="owner-option-list">
          {dates.map((option) => (
            <article className="owner-option-card" key={option.local_key}>
              <div className="comfortable-form two-column">
                <label>
                  Label
                  <input
                    value={option.label}
                    onChange={(event) =>
                      updateDate(option.local_key, "label", event.target.value)
                    }
                    required
                  />
                </label>
                <label>
                  Starts
                  <input
                    type="datetime-local"
                    value={option.start_datetime}
                    onChange={(event) =>
                      updateDate(
                        option.local_key,
                        "start_datetime",
                        event.target.value,
                      )
                    }
                    required
                  />
                </label>
                <label>
                  Ends
                  <input
                    type="datetime-local"
                    value={option.end_datetime ?? ""}
                    onChange={(event) =>
                      updateDate(
                        option.local_key,
                        "end_datetime",
                        event.target.value || null,
                      )
                    }
                  />
                </label>
                <label>
                  Timezone
                  <input
                    value={option.venue_timezone}
                    onChange={(event) =>
                      updateDate(
                        option.local_key,
                        "venue_timezone",
                        event.target.value,
                      )
                    }
                    required
                  />
                </label>
              </div>
              <button
                className="icon-button danger-icon"
                type="button"
                onClick={() => removeDate(option)}
                aria-label={`Remove ${option.label}`}
              >
                <Trash2 />
              </button>
            </article>
          ))}
        </div>

        <div className="owner-option-heading">
          <strong>Ticket-price choices</strong>
          <button
            className="button secondary compact"
            type="button"
            onClick={() =>
              setPrices((current) => [
                ...current,
                {
                  local_key: crypto.randomUUID(),
                  amount: "50.00",
                  currency: form.currency,
                  label: `Price option ${current.length + 1}`,
                  active: true,
                },
              ])
            }
          >
            <Plus size={16} /> Add price
          </button>
        </div>

        <div className="owner-option-list">
          {prices.map((option) => (
            <article className="owner-option-card price-option-card" key={option.local_key}>
              <CircleDollarSign />
              <div className="comfortable-form owner-price-grid">
                <label>
                  Label
                  <input
                    value={option.label}
                    onChange={(event) =>
                      updatePrice(option.local_key, "label", event.target.value)
                    }
                    required
                  />
                </label>
                <label>
                  Amount
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={option.amount}
                    onChange={(event) =>
                      updatePrice(option.local_key, "amount", event.target.value)
                    }
                    required
                  />
                </label>
                <label>
                  Currency
                  <input
                    maxLength={3}
                    value={option.currency}
                    onChange={(event) =>
                      updatePrice(
                        option.local_key,
                        "currency",
                        event.target.value.toUpperCase(),
                      )
                    }
                    required
                  />
                </label>
              </div>
              <button
                className="icon-button danger-icon"
                type="button"
                onClick={() => removePrice(option)}
                aria-label={`Remove ${option.label}`}
              >
                <Trash2 />
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="owner-edit-section">
        <div className="subsection-heading">
          <CircleDollarSign />
          <div>
            <strong>Thresholds and organizer</strong>
            <span>Changes are audited and the campaign status remains unchanged.</span>
          </div>
        </div>
        <div className="comfortable-form two-column">
          <label>
            Goal type
            <select
              value={form.goal_type}
              onChange={(event) =>
                setForm({ ...form, goal_type: event.target.value as GoalType })
              }
            >
              <option value="supporters">Supporter quantity</option>
              <option value="money">Committed amount</option>
              <option value="both">Both targets</option>
            </select>
          </label>
          <label>
            Deadline
            <input
              type="datetime-local"
              value={form.deadline}
              onChange={(event) =>
                setForm({ ...form, deadline: event.target.value })
              }
              required
            />
          </label>
          <label>
            Supporter target
            <input
              type="number"
              min="1"
              value={form.supporter_target}
              onChange={(event) =>
                setForm({ ...form, supporter_target: Number(event.target.value) })
              }
              required
            />
          </label>
          <label>
            Commitment target
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.amount_target}
              onChange={(event) =>
                setForm({ ...form, amount_target: event.target.value })
              }
              required
            />
          </label>
          <label>
            Suggested refundable deposit
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.suggested_deposit}
              onChange={(event) =>
                setForm({ ...form, suggested_deposit: event.target.value })
              }
              required
            />
          </label>
          <label>
            Currency
            <input
              maxLength={3}
              value={form.currency}
              onChange={(event) =>
                setForm({ ...form, currency: event.target.value.toUpperCase() })
              }
              required
            />
          </label>
          <label>
            Organizer name
            <input
              value={form.organizer_name}
              onChange={(event) =>
                setForm({ ...form, organizer_name: event.target.value })
              }
              required
            />
          </label>
          <label>
            Organizer email
            <input
              type="email"
              value={form.organizer_email}
              onChange={(event) =>
                setForm({ ...form, organizer_email: event.target.value })
              }
              required
            />
          </label>
          <label className="full-width">
            Facebook Event URL
            <input
              type="url"
              value={form.facebook_event_url}
              onChange={(event) =>
                setForm({ ...form, facebook_event_url: event.target.value })
              }
            />
          </label>
          <label className="full-width">
            Facebook Group URL
            <input
              type="url"
              value={form.facebook_group_url}
              onChange={(event) =>
                setForm({ ...form, facebook_group_url: event.target.value })
              }
            />
          </label>
          <label className="full-width">
            Facebook Page URL
            <input
              type="url"
              value={form.facebook_page_url}
              onChange={(event) =>
                setForm({ ...form, facebook_page_url: event.target.value })
              }
            />
          </label>
        </div>
      </section>

      {(error || message) && (
        <div className={`notice ${error ? "error-notice" : "owner-edit-success"}`} role={error ? "alert" : "status"}>
          {error ? error : <><Check size={17} /> {message}</>}
        </div>
      )}

      <div className="owner-edit-actions">
        <button className="button ghost" type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button className="button primary" disabled={busy}>
          <Save size={17} />
          {busy ? "Saving full seed…" : "Save campaign seed"}
        </button>
      </div>
    </form>
  );
}
