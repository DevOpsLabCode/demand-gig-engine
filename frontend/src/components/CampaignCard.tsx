/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Presents one campaign through a compact summary and progressively disclosed voting, funding, and organizer tools.
 */

import { FormEvent, useMemo, useState } from "react";
import { Elements } from "@stripe/react-stripe-js";
import {
  BadgeDollarSign,
  Banknote,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  ExternalLink,
  Facebook,
  MapPin,
  MonitorPlay,
  MoreHorizontal,
  ShieldCheck,
  Share2,
  Sparkles,
  TicketCheck,
  Users,
} from "lucide-react";
import type {
  Campaign,
  PledgeInput,
  PledgeResult,
  SponsorInput,
  SupporterPreference,
  SupporterPreferenceInput,
} from "../types";
import { stripePromise } from "../stripe";
import { DepositPayment } from "./DepositPayment";
import { FacebookIntegration } from "./FacebookIntegration";
import { SupporterPreferenceForm } from "./SupporterPreferenceForm";
import { trackMetaEvent } from "../meta";

interface Props {
  campaign: Campaign;
  authenticated: boolean;
  onSubmitReview: (slug: string) => Promise<Campaign>;
  onApprove: (slug: string, notes: string) => Promise<Campaign>;
  onReject: (slug: string, notes: string) => Promise<Campaign>;
  onLaunch: (slug: string) => Promise<Campaign>;
  onPreference: (
    slug: string,
    data: SupporterPreferenceInput,
  ) => Promise<SupporterPreference>;
  onPledge: (slug: string, data: PledgeInput) => Promise<PledgeResult>;
  onSponsor: (slug: string, data: SponsorInput) => Promise<void>;
  onReload: () => Promise<void>;
}

type CampaignTab = "overview" | "vote" | "funding" | "tools";

const VOTING_STATUSES = new Set([
  "approved",
  "collecting",
  "target_reached",
  "threshold_reached",
  "feasibility_review",
  "conditionally_ready",
  "ready",
]);

const FUNDING_STATUSES = new Set([
  "collecting",
  "target_reached",
  "threshold_reached",
]);

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  pending_review: "Needs review",
  approved: "Approved",
  collecting: "Building demand",
  target_reached: "Target reached",
  threshold_reached: "Threshold reached",
  feasibility_review: "Feasibility review",
  conditionally_ready: "Conditionally ready",
  ready: "Ready to confirm",
  confirmed: "Confirmed",
  live: "Live",
  completed: "Completed",
  rejected: "Changes requested",
  expired: "Expired",
  cancelled: "Cancelled",
  canceled: "Cancelled",
  failed: "Not viable",
  refund_pending: "Refund pending",
  refunding: "Refunding",
  refunded: "Refunded",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function statusTone(status: string) {
  if (["target_reached", "threshold_reached", "ready", "confirmed", "live", "completed"].includes(status)) {
    return "success";
  }
  if (["pending_review", "feasibility_review", "conditionally_ready"].includes(status)) {
    return "warning";
  }
  if (["rejected", "expired", "cancelled", "canceled", "failed", "refunding", "refunded"].includes(status)) {
    return "muted";
  }
  return "accent";
}

export function CampaignCard({
  campaign,
  authenticated,
  onSubmitReview,
  onApprove,
  onReject,
  onLaunch,
  onPreference,
  onPledge,
  onSponsor,
  onReload,
}: Props) {
  const money = (value: string | number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: campaign.currency,
      maximumFractionDigits: 2,
    }).format(Number(value));

  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const [activeTab, setActiveTab] = useState<CampaignTab>("overview");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [amount, setAmount] = useState(campaign.suggested_deposit);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [clientSecret, setClientSecret] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [showSponsor, setShowSponsor] = useState(false);
  const [sponsor, setSponsor] = useState<SponsorInput>({
    sponsor_name: "",
    contact_name: "",
    contact_email: "",
    amount: "1000.00",
    benefits_requested: "",
  });

  const failedChecks =
    campaign.latest_review?.checks.filter((check) => !check.passed) ?? [];
  const summary = campaign.preference_summary;
  const canVote = VOTING_STATUSES.has(campaign.status);
  const canFund = FUNDING_STATUSES.has(campaign.status);
  const progress = Math.max(0, Math.min(100, campaign.progress_percent));

  async function runApprovalChecks() {
    setBusy(true);
    setMessage("");
    try {
      const result = await onSubmitReview(campaign.slug);
      setMessage(
        result.status === "approved"
          ? "All approval checks passed. The campaign is ready to launch."
          : "Some checks need administrator review.",
      );
      setActiveTab("tools");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not submit campaign");
    } finally {
      setBusy(false);
    }
  }

  async function launchApprovedCampaign() {
    setBusy(true);
    setMessage("");
    try {
      await onLaunch(campaign.slug);
      setMessage("Campaign launched and is now collecting support.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not launch campaign");
    } finally {
      setBusy(false);
    }
  }

  async function reviewCampaign(decision: "approve" | "reject") {
    if (decision === "reject" && !reviewNotes.trim()) {
      setMessage("Add written notes before requesting changes.");
      return;
    }

    setBusy(true);
    setMessage("");
    try {
      if (decision === "approve") {
        await onApprove(campaign.slug, reviewNotes);
        setMessage("Campaign approved after administrator review.");
      } else {
        await onReject(campaign.slug, reviewNotes);
        setMessage("Campaign returned to its owner with review notes.");
      }
      setReviewNotes("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not complete review");
    } finally {
      setBusy(false);
    }
  }

  async function pledge(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      const result = await onPledge(campaign.slug, {
        supporter_name: name,
        supporter_email: email,
        quantity: 1,
        amount,
        idempotency_key: crypto.randomUUID(),
        source: params.get("source") ?? "direct",
        source_label: params.get("group") ?? "",
        referral_code: params.get("ref") ?? "",
      });

      trackMetaEvent(
        result.client_secret ? "InitiateCheckout" : "Lead",
        {
          value: Number(amount),
          currency: campaign.currency,
          content_name: campaign.title,
          content_category: "demand_driven_gig",
        },
        `pledge:${result.pledge.id}:created`,
      );

      if (result.client_secret) {
        setClientSecret(result.client_secret);
        setMessage("Complete the refundable deposit below.");
      } else {
        setMessage("Your support was recorded.");
        setName("");
        setEmail("");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not record support");
    } finally {
      setBusy(false);
    }
  }

  async function submitSponsor(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      await onSponsor(campaign.slug, sponsor);
      setMessage("Sponsor commitment recorded.");
      setShowSponsor(false);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not record sponsorship");
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const url = `${window.location.origin}/?campaign=${campaign.slug}&source=shared_campaign`;
    const data = { title: campaign.title, text: campaign.pitch, url };

    try {
      if (navigator.share) {
        await navigator.share(data);
      } else {
        await navigator.clipboard.writeText(url);
        setMessage("Campaign link copied.");
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setMessage("Sharing is unavailable. Copy the page URL from your browser.");
    }
  }

  function openPrimaryAction() {
    if (campaign.status === "pending_review" && campaign.can_review_campaign) {
      setActiveTab("tools");
      return;
    }
    if (canVote) {
      setActiveTab("vote");
      return;
    }
    if (canFund) {
      setActiveTab("funding");
      return;
    }
    setActiveTab("overview");
  }

  const primaryLabel =
    campaign.status === "pending_review" && campaign.can_review_campaign
      ? "Review campaign"
      : canVote
        ? campaign.my_preference
          ? "Update my vote"
          : "Vote on this gig"
        : canFund
          ? "Support this gig"
          : "View campaign";

  return (
    <article className="campaign-card">
      <div className="campaign-card-top">
        <div className="campaign-identity">
          <div className="campaign-badges">
            <span className={`status-badge ${statusTone(campaign.status)}`}>
              {STATUS_LABELS[campaign.status] ?? campaign.status.replaceAll("_", " ")}
            </span>
            {campaign.my_preference && (
              <span className="status-badge voted">
                <Check size={13} />
                Voted
              </span>
            )}
          </div>
          <h3>{campaign.title}</h3>
          <div className="campaign-meta">
            <span><MapPin size={15} /> {campaign.city}</span>
            <span><Clock3 size={15} /> Ends {formatDate(campaign.deadline)}</span>
          </div>
        </div>
        <button
          className="icon-button"
          type="button"
          onClick={share}
          aria-label={`Share ${campaign.title}`}
        >
          <Share2 />
        </button>
      </div>

      <p className="campaign-pitch">{campaign.pitch}</p>

      <div className="campaign-progress-block">
        <div className="progress-label">
          <span>Minimum demand</span>
          <strong>{progress}%</strong>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label="Campaign progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
        >
          <span style={{ width: `${progress}%` }} />
        </div>
        <div className="campaign-summary-grid">
          <div>
            <Users size={17} />
            <span>Expected audience</span>
            <strong>{summary.expected_attendance.toLocaleString()}</strong>
          </div>
          <div>
            <TicketCheck size={17} />
            <span>Pledged quantity</span>
            <strong>{campaign.active_supporter_count.toLocaleString()}</strong>
          </div>
          <div>
            <BadgeDollarSign size={17} />
            <span>Conditional funding</span>
            <strong>{money(summary.total_conditional_funding)}</strong>
          </div>
        </div>
      </div>

      <div className="confirmation-strip" aria-label="Confirmation status">
        <span className={campaign.artist_confirmed ? "is-confirmed" : ""}>
          <CheckCircle2 size={16} />
          Artist {campaign.artist_confirmed ? "confirmed" : "pending"}
        </span>
        <span className={campaign.venue_confirmed ? "is-confirmed" : ""}>
          <CheckCircle2 size={16} />
          Venue {campaign.venue_confirmed ? "confirmed" : "pending"}
        </span>
      </div>

      <div className="campaign-primary-actions">
        {["draft", "rejected"].includes(campaign.status) && campaign.can_manage ? (
          <button
            className="button primary"
            type="button"
            disabled={busy}
            onClick={runApprovalChecks}
          >
            <ShieldCheck size={17} />
            {busy ? "Checking…" : "Run approval checks"}
          </button>
        ) : campaign.status === "approved" && campaign.can_manage ? (
          <button
            className="button primary"
            type="button"
            disabled={busy}
            onClick={launchApprovedCampaign}
          >
            <Sparkles size={17} />
            {busy ? "Launching…" : "Start collecting support"}
          </button>
        ) : (
          <button className="button primary" type="button" onClick={openPrimaryAction}>
            {primaryLabel}
            <ChevronRight size={17} />
          </button>
        )}
        <button
          className="button ghost"
          type="button"
          onClick={() => setActiveTab(activeTab === "overview" ? "tools" : "overview")}
        >
          <MoreHorizontal size={18} />
          Details
        </button>
      </div>

      <div className="campaign-tabs" role="tablist" aria-label={`${campaign.title} sections`}>
        {([
          ["overview", "Overview"],
          ["vote", "Vote"],
          ["funding", "Funding"],
          ["tools", campaign.can_manage || campaign.can_review_campaign ? "Manage" : "More"],
        ] as [CampaignTab, string][]).map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={activeTab === value}
            className={activeTab === value ? "is-active" : ""}
            onClick={() => setActiveTab(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="campaign-tab-panel" role="tabpanel">
        {activeTab === "overview" && (
          <div className="overview-stack">
            <div className="forecast-grid">
              <div className="forecast-card">
                <Users />
                <span>Physical attendance</span>
                <strong>{summary.physical_expected_attendance.toLocaleString()}</strong>
              </div>
              <div className="forecast-card">
                <MonitorPlay />
                <span>Virtual attendance</span>
                <strong>{summary.virtual_expected_attendance.toLocaleString()}</strong>
              </div>
              <div className="forecast-card">
                <CircleDollarSign />
                <span>Projected ticket revenue</span>
                <strong>{money(summary.projected_ticket_revenue)}</strong>
              </div>
            </div>

            <div className="result-columns">
              <section>
                <div className="subsection-heading">
                  <CalendarDays size={17} />
                  <strong>Popular dates</strong>
                </div>
                {summary.date_results.length > 0 ? (
                  <ol className="ranked-list">
                    {summary.date_results.map((result) => (
                      <li key={result.option_id}>
                        <div>
                          <strong>{result.label || formatDate(result.start_datetime)}</strong>
                          <span>{formatDate(result.start_datetime)}</span>
                        </div>
                        <span>{result.expected_attendance} expected</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="empty-copy">No date votes yet.</p>
                )}
              </section>

              <section>
                <div className="subsection-heading">
                  <TicketCheck size={17} />
                  <strong>Acceptable prices</strong>
                </div>
                {summary.price_results.length > 0 ? (
                  <ol className="ranked-list">
                    {summary.price_results.map((result) => (
                      <li key={result.option_id}>
                        <div>
                          <strong>{result.label || money(result.amount)}</strong>
                          <span>{money(result.amount)}</span>
                        </div>
                        <span>{result.expected_attendance} expected</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="empty-copy">No price votes yet.</p>
                )}
              </section>
            </div>

            <div className="financial-note">
              <Banknote size={18} />
              <p>
                Projected ticket revenue is a forecast. Deposits and sponsorships
                remain separate conditional commitments.
              </p>
            </div>
          </div>
        )}

        {activeTab === "vote" && (
          <SupporterPreferenceForm
            campaign={campaign}
            authenticated={authenticated}
            onSave={onPreference}
          />
        )}

        {activeTab === "funding" && (
          <div className="funding-stack">
            <div className="forecast-grid compact-forecast">
              <div className="forecast-card">
                <BadgeDollarSign />
                <span>Deposits collected</span>
                <strong>{money(summary.deposits_collected)}</strong>
              </div>
              <div className="forecast-card">
                <Banknote />
                <span>Sponsor commitments</span>
                <strong>{money(summary.sponsor_commitments)}</strong>
              </div>
            </div>

            {canFund ? (
              <>
                <div className="subsection-heading">
                  <BadgeDollarSign size={18} />
                  <div>
                    <strong>Support the campaign</strong>
                    <span>Deposits are refundable under the published campaign terms.</span>
                  </div>
                </div>
                <form className="comfortable-form pledge-form" onSubmit={pledge}>
                  <label>
                    Your name
                    <input
                      autoComplete="name"
                      placeholder="Full name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Email
                    <input
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Refundable deposit
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={amount}
                      onChange={(event) => setAmount(event.target.value)}
                    />
                  </label>
                  <button className="button primary" disabled={busy}>
                    {busy ? "Recording…" : "Support this gig"}
                  </button>
                </form>

                <button
                  className="button secondary"
                  type="button"
                  onClick={() => setShowSponsor((value) => !value)}
                  aria-expanded={showSponsor}
                >
                  <Banknote size={17} />
                  {showSponsor ? "Close sponsor form" : "Support as a sponsor"}
                </button>

                {showSponsor && (
                  <form className="comfortable-form sponsor-form" onSubmit={submitSponsor}>
                    <label>
                      Sponsor or company
                      <input
                        value={sponsor.sponsor_name}
                        onChange={(event) =>
                          setSponsor({ ...sponsor, sponsor_name: event.target.value })
                        }
                        required
                      />
                    </label>
                    <label>
                      Contact name
                      <input
                        autoComplete="name"
                        value={sponsor.contact_name}
                        onChange={(event) =>
                          setSponsor({ ...sponsor, contact_name: event.target.value })
                        }
                        required
                      />
                    </label>
                    <label>
                      Contact email
                      <input
                        type="email"
                        autoComplete="email"
                        value={sponsor.contact_email}
                        onChange={(event) =>
                          setSponsor({ ...sponsor, contact_email: event.target.value })
                        }
                        required
                      />
                    </label>
                    <label>
                      Commitment amount
                      <input
                        type="number"
                        min="1"
                        step="0.01"
                        value={sponsor.amount}
                        onChange={(event) =>
                          setSponsor({ ...sponsor, amount: event.target.value })
                        }
                        required
                      />
                    </label>
                    <label className="full-width">
                      Requested benefits
                      <textarea
                        rows={3}
                        value={sponsor.benefits_requested}
                        onChange={(event) =>
                          setSponsor({
                            ...sponsor,
                            benefits_requested: event.target.value,
                          })
                        }
                        placeholder="Optional visibility, hospitality, or activation request"
                      />
                    </label>
                    <button className="button primary" disabled={busy}>
                      Commit sponsorship
                    </button>
                  </form>
                )}
              </>
            ) : (
              <div className="notice">
                Funding is not open in the campaign’s current lifecycle state.
              </div>
            )}

            {clientSecret && stripePromise && (
              <Elements stripe={stripePromise} options={{ clientSecret }}>
                <DepositPayment
                  onSuccess={async () => {
                    setClientSecret("");
                    setMessage("Deposit received. Thank you for supporting this campaign.");
                    await onReload();
                  }}
                />
              </Elements>
            )}
            {clientSecret && !stripePromise && (
              <p className="error">
                Set VITE_STRIPE_PUBLISHABLE_KEY to complete Stripe deposits.
              </p>
            )}
          </div>
        )}

        {activeTab === "tools" && (
          <div className="tools-stack">
            {campaign.latest_review && (
              <section className="review-panel">
                <div className="subsection-heading">
                  <ShieldCheck size={18} />
                  <div>
                    <strong>Approval review</strong>
                    <span>{campaign.latest_review.notes}</span>
                  </div>
                </div>
                {failedChecks.length > 0 && (
                  <ul className="check-list failed">
                    {failedChecks.map((check) => (
                      <li key={check.key}>{check.message}</li>
                    ))}
                  </ul>
                )}
              </section>
            )}

            {campaign.status === "pending_review" && !campaign.can_review_campaign && (
              <div className="notice">
                Automatic checks require administrator review. Any failed
                conditions appear above.
              </div>
            )}

            {campaign.status === "pending_review" && campaign.can_review_campaign && (
              <section className="review-controls">
                <div className="subsection-heading">
                  <ShieldCheck size={18} />
                  <div>
                    <strong>Administrator decision</strong>
                    <span>Approval notes are optional. Rejection notes are required.</span>
                  </div>
                </div>
                <label>
                  Review notes
                  <textarea
                    rows={4}
                    placeholder="Explain the decision clearly and constructively"
                    value={reviewNotes}
                    onChange={(event) => setReviewNotes(event.target.value)}
                  />
                </label>
                <div className="button-row">
                  <button
                    className="button primary"
                    type="button"
                    disabled={busy}
                    onClick={() => reviewCampaign("approve")}
                  >
                    Approve campaign
                  </button>
                  <button
                    className="button danger"
                    type="button"
                    disabled={busy}
                    onClick={() => reviewCampaign("reject")}
                  >
                    Request changes
                  </button>
                </div>
              </section>
            )}

            {(campaign.facebook_event_url ||
              campaign.facebook_group_url ||
              campaign.facebook_page_url) && (
              <section>
                <div className="subsection-heading">
                  <Facebook size={18} />
                  <strong>Community links</strong>
                </div>
                <div className="external-link-row">
                  {campaign.facebook_event_url && (
                    <a href={campaign.facebook_event_url} target="_blank" rel="noreferrer">
                      Facebook Event <ExternalLink size={14} />
                    </a>
                  )}
                  {campaign.facebook_group_url && (
                    <a href={campaign.facebook_group_url} target="_blank" rel="noreferrer">
                      Facebook Group <ExternalLink size={14} />
                    </a>
                  )}
                  {campaign.facebook_page_url && (
                    <a href={campaign.facebook_page_url} target="_blank" rel="noreferrer">
                      Facebook Page <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              </section>
            )}

            <FacebookIntegration campaign={campaign} onMessage={setMessage} />

            <small>
              Deposits are refundable when the campaign misses its target or
              cannot confirm the artist and venue under the published terms.
            </small>
          </div>
        )}
      </div>

      {message && (
        <div className="toast-message" role="status" aria-live="polite">
          {message}
        </div>
      )}
    </article>
  );
}
