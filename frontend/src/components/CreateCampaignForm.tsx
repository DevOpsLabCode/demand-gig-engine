/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Guides organizers through a comfortable four-step campaign creation workflow.
 */

import { FormEvent, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CalendarPlus,
  Check,
  CircleDollarSign,
  Flag,
  Link2,
  Plus,
  Rocket,
  Sprout,
  Trash2,
  UserRound,
} from "lucide-react";
import type {
  CampaignCreate,
  CampaignDateOptionInput,
  CampaignPriceOptionInput,
  GoalType,
} from "../types";

interface Props {
  onCreate: (campaign: CampaignCreate) => Promise<void>;
}

const STEPS = [
  { label: "Basics", icon: Sprout },
  { label: "Dates & prices", icon: CalendarPlus },
  { label: "Goal & organizer", icon: Flag },
  { label: "Review", icon: Check },
];

function futureLocal(days: number, hour = 19): string {
  const value = new Date();
  value.setDate(value.getDate() + days);
  value.setHours(hour, 0, 0, 0);
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 16);
}

function defaultDates(): CampaignDateOptionInput[] {
  return [
    {
      start_datetime: futureLocal(45),
      end_datetime: futureLocal(45, 22),
      venue_timezone: "America/New_York",
      label: "Friday night",
      active: true,
    },
  ];
}

function defaultPrices(): CampaignPriceOptionInput[] {
  return [
    {
      amount: "35.00",
      currency: "USD",
      label: "Standard ticket",
      active: true,
    },
  ];
}

export function CreateCampaignForm({ onCreate }: Props) {
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<CampaignCreate>({
    title: "",
    pitch: "",
    artist_name: "",
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
    organizer_email: "",
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

  const money = useMemo(
    () =>
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: form.currency || "USD",
        maximumFractionDigits: 2,
      }),
    [form.currency],
  );

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

  function validateCurrentStep() {
    if (step === 0) {
      if (
        !form.title.trim() ||
        !form.artist_name.trim() ||
        !form.city.trim() ||
        !form.country.trim() ||
        !form.pitch.trim()
      ) {
        return "Complete the campaign title, artist, location, and pitch.";
      }
    }

    if (step === 1) {
      if (form.date_options.length === 0 || form.price_options.length === 0) {
        return "Add at least one proposed date and one ticket-price choice.";
      }
      if (
        form.date_options.some(
          (option) =>
            !option.label.trim() ||
            !option.start_datetime ||
            !option.venue_timezone.trim(),
        )
      ) {
        return "Complete every proposed date.";
      }
      if (
        form.price_options.some(
          (option) =>
            !option.label.trim() ||
            Number(option.amount) < 0 ||
            !option.currency.trim(),
        )
      ) {
        return "Complete every ticket-price option.";
      }
    }

    if (step === 2) {
      if (!form.deadline || !form.organizer_name.trim() || !form.organizer_email.trim()) {
        return "Complete the deadline and organizer contact information.";
      }
      if (form.supporter_target < 1) {
        return "The supporter target must be at least one.";
      }
    }

    return "";
  }

  function nextStep() {
    const validationError = validateCurrentStep();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setStep((current) => Math.min(STEPS.length - 1, current + 1));
  }

  function previousStep() {
    setError("");
    setStep((current) => Math.max(0, current - 1));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    if (step < STEPS.length - 1) {
      nextStep();
      return;
    }

    setBusy(true);
    setError("");

    try {
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
    <form className="campaign-wizard" onSubmit={submit}>
      <ol className="wizard-steps" aria-label="Campaign creation progress">
        {STEPS.map(({ label, icon: Icon }, index) => (
          <li
            key={label}
            className={index === step ? "is-current" : index < step ? "is-complete" : ""}
            aria-current={index === step ? "step" : undefined}
          >
            <button
              type="button"
              onClick={() => {
                if (index <= step) {
                  setStep(index);
                  setError("");
                }
              }}
              disabled={index > step}
            >
              <span>{index < step ? <Check /> : <Icon />}</span>
              <small>Step {index + 1}</small>
              <strong>{label}</strong>
            </button>
          </li>
        ))}
      </ol>

      <div className="wizard-panel">
        {step === 0 && (
          <section className="wizard-section" aria-labelledby="wizard-basics">
            <div className="wizard-section-heading">
              <span className="wizard-icon"><Sprout /></span>
              <div>
                <h3 id="wizard-basics">Start with the campaign idea</h3>
                <p>Use a clear, specific title that fans can understand in seconds.</p>
              </div>
            </div>

            <div className="comfortable-form two-column">
              <label className="full-width">
                Campaign title
                <input
                  value={form.title}
                  onChange={(event) => set("title", event.target.value)}
                  placeholder="Bring Gogol Bordello to New York"
                  autoFocus
                  required
                />
                <small>Describe the desired artist and city, not an abstract project name.</small>
              </label>
              <label>
                Artist or band
                <input
                  value={form.artist_name}
                  onChange={(event) => set("artist_name", event.target.value)}
                  placeholder="Artist name"
                  required
                />
              </label>
              <label>
                City
                <input
                  value={form.city}
                  onChange={(event) => set("city", event.target.value)}
                  placeholder="New York"
                  required
                />
              </label>
              <label>
                Country
                <input
                  value={form.country}
                  onChange={(event) => set("country", event.target.value)}
                  placeholder="United States"
                  required
                />
              </label>
              <label className="full-width">
                Why should this event happen?
                <textarea
                  value={form.pitch}
                  onChange={(event) => set("pitch", event.target.value)}
                  rows={5}
                  placeholder="Explain the audience, the experience, and why proving demand reduces risk."
                  required
                />
                <small>Keep the opening concise. Detailed logistics can be added later.</small>
              </label>
            </div>
          </section>
        )}

        {step === 1 && (
          <section className="wizard-section" aria-labelledby="wizard-options">
            <div className="wizard-section-heading">
              <span className="wizard-icon"><CalendarPlus /></span>
              <div>
                <h3 id="wizard-options">Offer realistic choices</h3>
                <p>Multiple dates and prices help measure demand before commitments are final.</p>
              </div>
            </div>

            <div className="option-builder">
              <div className="option-builder-heading">
                <div>
                  <strong>Proposed dates</strong>
                  <span>Supporters choose one preferred date.</span>
                </div>
                <button
                  className="button secondary compact"
                  type="button"
                  onClick={() =>
                    set("date_options", [
                      ...form.date_options,
                      {
                        start_datetime: futureLocal(60),
                        end_datetime: futureLocal(60, 22),
                        venue_timezone: "America/New_York",
                        label: `Date option ${form.date_options.length + 1}`,
                        active: true,
                      },
                    ])
                  }
                >
                  <Plus size={16} />
                  Add date
                </button>
              </div>

              <div className="builder-list">
                {form.date_options.map((option, index) => (
                  <article className="builder-card" key={`date-${index}`}>
                    <span className="builder-number">{index + 1}</span>
                    <div className="comfortable-form builder-grid">
                      <label>
                        Friendly label
                        <input
                          value={option.label}
                          onChange={(event) =>
                            updateDate(index, "label", event.target.value)
                          }
                          placeholder="Friday night"
                          required
                        />
                      </label>
                      <label>
                        Starts
                        <input
                          type="datetime-local"
                          value={option.start_datetime}
                          onChange={(event) =>
                            updateDate(index, "start_datetime", event.target.value)
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
                              index,
                              "end_datetime",
                              event.target.value || null,
                            )
                          }
                        />
                      </label>
                      <label>
                        Venue timezone
                        <input
                          value={option.venue_timezone}
                          onChange={(event) =>
                            updateDate(index, "venue_timezone", event.target.value)
                          }
                          required
                        />
                      </label>
                    </div>
                    <button
                      className="icon-button danger-icon"
                      type="button"
                      disabled={form.date_options.length === 1}
                      onClick={() =>
                        set(
                          "date_options",
                          form.date_options.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        )
                      }
                      aria-label={`Remove date option ${index + 1}`}
                    >
                      <Trash2 />
                    </button>
                  </article>
                ))}
              </div>
            </div>

            <div className="option-builder">
              <div className="option-builder-heading">
                <div>
                  <strong>Acceptable ticket prices</strong>
                  <span>These are demand forecasts, not charges.</span>
                </div>
                <button
                  className="button secondary compact"
                  type="button"
                  onClick={() =>
                    set("price_options", [
                      ...form.price_options,
                      {
                        amount: "50.00",
                        currency: form.currency,
                        label: `Price option ${form.price_options.length + 1}`,
                        active: true,
                      },
                    ])
                  }
                >
                  <Plus size={16} />
                  Add price
                </button>
              </div>

              <div className="builder-list price-builder-list">
                {form.price_options.map((option, index) => (
                  <article className="builder-card price-builder-card" key={`price-${index}`}>
                    <span className="builder-number">{index + 1}</span>
                    <CircleDollarSign className="builder-leading-icon" />
                    <div className="comfortable-form builder-grid price-builder-grid">
                      <label>
                        Label
                        <input
                          value={option.label}
                          onChange={(event) =>
                            updatePrice(index, "label", event.target.value)
                          }
                          placeholder="Standard ticket"
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
                            updatePrice(index, "amount", event.target.value)
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
                              index,
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
                      disabled={form.price_options.length === 1}
                      onClick={() =>
                        set(
                          "price_options",
                          form.price_options.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        )
                      }
                      aria-label={`Remove price option ${index + 1}`}
                    >
                      <Trash2 />
                    </button>
                  </article>
                ))}
              </div>
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="wizard-section" aria-labelledby="wizard-goal">
            <div className="wizard-section-heading">
              <span className="wizard-icon"><Flag /></span>
              <div>
                <h3 id="wizard-goal">Define what makes the event viable</h3>
                <p>Set transparent targets and give supporters a trusted organizer contact.</p>
              </div>
            </div>

            <div className="comfortable-form two-column">
              <label>
                Goal type
                <select
                  value={form.goal_type}
                  onChange={(event) =>
                    set("goal_type", event.target.value as GoalType)
                  }
                >
                  <option value="supporters">Supporter quantity</option>
                  <option value="money">Committed amount</option>
                  <option value="both">Both supporter and amount targets</option>
                </select>
              </label>
              <label>
                Campaign deadline
                <input
                  type="datetime-local"
                  value={form.deadline}
                  onChange={(event) => set("deadline", event.target.value)}
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
                    set("supporter_target", Number(event.target.value))
                  }
                />
              </label>
              <label>
                Commitment target
                <span className="input-prefix">
                  <span>{form.currency}</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.amount_target}
                    onChange={(event) => set("amount_target", event.target.value)}
                  />
                </span>
              </label>
              <label>
                Suggested refundable deposit
                <span className="input-prefix">
                  <span>{form.currency}</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.suggested_deposit}
                    onChange={(event) =>
                      set("suggested_deposit", event.target.value)
                    }
                  />
                </span>
                <small>Zero-dollar support remains allowed.</small>
              </label>
              <label>
                Currency
                <input
                  maxLength={3}
                  value={form.currency}
                  onChange={(event) =>
                    set("currency", event.target.value.toUpperCase())
                  }
                  required
                />
              </label>
            </div>

            <div className="form-divider" />

            <div className="wizard-section-heading small-heading">
              <span className="wizard-icon"><UserRound /></span>
              <div>
                <h4>Organizer contact</h4>
                <p>This information supports approval and accountability.</p>
              </div>
            </div>

            <div className="comfortable-form two-column">
              <label>
                Organizer name
                <input
                  value={form.organizer_name}
                  onChange={(event) => set("organizer_name", event.target.value)}
                  required
                />
              </label>
              <label>
                Organizer email
                <input
                  type="email"
                  autoComplete="email"
                  value={form.organizer_email}
                  onChange={(event) => set("organizer_email", event.target.value)}
                  placeholder="organizer@example.com"
                  required
                />
              </label>
            </div>

            <details className="optional-preferences social-links">
              <summary>
                <Link2 size={17} />
                Add existing Facebook community links
              </summary>
              <div className="comfortable-form">
                <label>
                  Facebook Event URL
                  <input
                    type="url"
                    value={form.facebook_event_url ?? ""}
                    onChange={(event) =>
                      set("facebook_event_url", event.target.value)
                    }
                    placeholder="https://www.facebook.com/events/..."
                  />
                </label>
                <label>
                  Primary Facebook Group URL
                  <input
                    type="url"
                    value={form.facebook_group_url ?? ""}
                    onChange={(event) =>
                      set("facebook_group_url", event.target.value)
                    }
                    placeholder="https://www.facebook.com/groups/..."
                  />
                </label>
                <label>
                  Facebook Page URL
                  <input
                    type="url"
                    value={form.facebook_page_url ?? ""}
                    onChange={(event) =>
                      set("facebook_page_url", event.target.value)
                    }
                    placeholder="https://www.facebook.com/..."
                  />
                </label>
              </div>
            </details>
          </section>
        )}

        {step === 3 && (
          <section className="wizard-section" aria-labelledby="wizard-review">
            <div className="wizard-section-heading">
              <span className="wizard-icon"><Rocket /></span>
              <div>
                <h3 id="wizard-review">Review before creating the draft</h3>
                <p>The campaign will still pass automatic approval checks before collecting support.</p>
              </div>
            </div>

            <div className="review-hero-card">
              <span className="status-badge accent">Draft preview</span>
              <h3>{form.title}</h3>
              <p>{form.pitch}</p>
              <div className="campaign-meta">
                <span>{form.artist_name}</span>
                <span>{form.city}, {form.country}</span>
              </div>
            </div>

            <div className="review-grid">
              <section>
                <strong>Campaign choices</strong>
                <dl>
                  <div><dt>Proposed dates</dt><dd>{form.date_options.length}</dd></div>
                  <div><dt>Ticket prices</dt><dd>{form.price_options.length}</dd></div>
                  <div>
                    <dt>Price range</dt>
                    <dd>
                      {money.format(
                        Math.min(...form.price_options.map((option) => Number(option.amount))),
                      )}
                      {" – "}
                      {money.format(
                        Math.max(...form.price_options.map((option) => Number(option.amount))),
                      )}
                    </dd>
                  </div>
                </dl>
              </section>
              <section>
                <strong>Viability target</strong>
                <dl>
                  <div><dt>Supporters</dt><dd>{form.supporter_target.toLocaleString()}</dd></div>
                  <div><dt>Commitments</dt><dd>{money.format(Number(form.amount_target))}</dd></div>
                  <div><dt>Suggested deposit</dt><dd>{money.format(Number(form.suggested_deposit))}</dd></div>
                </dl>
              </section>
              <section>
                <strong>Organizer</strong>
                <dl>
                  <div><dt>Name</dt><dd>{form.organizer_name}</dd></div>
                  <div><dt>Email</dt><dd>{form.organizer_email}</dd></div>
                  <div><dt>Deadline</dt><dd>{new Date(form.deadline).toLocaleString()}</dd></div>
                </dl>
              </section>
            </div>

            <div className="notice">
              <strong>What happens next</strong>
              <span>
                The draft is created first. Automatic checks approve complete,
                valid campaigns or route exceptions to an administrator.
              </span>
            </div>
          </section>
        )}

        {error && (
          <div className="notice error-notice" role="alert">
            {error}
          </div>
        )}

        <div className="wizard-actions">
          <button
            className="button ghost"
            type="button"
            onClick={previousStep}
            disabled={step === 0 || busy}
          >
            <ArrowLeft size={17} />
            Back
          </button>

          <span>Step {step + 1} of {STEPS.length}</span>

          {step < STEPS.length - 1 ? (
            <button className="button primary" type="button" onClick={nextStep}>
              Continue
              <ArrowRight size={17} />
            </button>
          ) : (
            <button className="button primary" disabled={busy}>
              <Rocket size={17} />
              {busy ? "Creating draft…" : "Create campaign draft"}
            </button>
          )}
        </div>
      </div>
    </form>
  );
}
