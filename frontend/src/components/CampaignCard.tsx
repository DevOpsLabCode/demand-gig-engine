/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Presents campaign approval, voting forecasts, progress, deposits, sponsorships, and sharing.
 */

import { FormEvent, useMemo, useState } from "react";
import { Elements } from "@stripe/react-stripe-js";
import {
  Banknote,
  CalendarDays,
  CheckCircle2,
  MapPin,
  MonitorPlay,
  ShieldCheck,
  Share2,
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
  const money = (value: string | number) => new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: campaign.currency,
    maximumFractionDigits: 2,
  }).format(Number(value));

  const params = useMemo(() => new URLSearchParams(window.location.search), []);
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

  const failedChecks = campaign.latest_review?.checks.filter((check) => !check.passed) ?? [];
  const summary = campaign.preference_summary;

  async function runApprovalChecks() {
    setBusy(true);
    setMessage("");
    try {
      const result = await onSubmitReview(campaign.slug);
      setMessage(
        result.status === "approved"
          ? "All deterministic checks passed. Campaign approved automatically."
          : "Automatic checks found issues. Campaign sent to administrator review.",
      );
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
      setMessage("Written rejection notes are required.");
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
        setMessage("You are helping make this gig happen.");
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
    const url = `${window.location.origin}/?campaign=${campaign.slug}&source=facebook_group`;
    const data = { title: campaign.title, text: campaign.pitch, url };
    if (navigator.share) await navigator.share(data);
    else {
      await navigator.clipboard.writeText(url);
      setMessage("Campaign link copied. Share it in the Facebook group.");
    }
  }

  return (
    <article className="panel campaign">
      <div className="campaign-heading">
        <div>
          <span className={`status ${campaign.status}`}>{campaign.status.replaceAll("_", " ")}</span>
          <h2>{campaign.title}</h2>
          <div className="meta">
            <span><MapPin size={16} /> {campaign.city}</span>
            <span><CalendarDays size={16} /> Ends {new Date(campaign.deadline).toLocaleDateString()}</span>
          </div>
        </div>
        <button className="icon-button" onClick={share} aria-label="Share campaign"><Share2 /></button>
      </div>

      <p>{campaign.pitch}</p>

      {campaign.latest_review && (
        <div className="review-summary">
          <strong><ShieldCheck size={17} /> Approval review</strong>
          <p>{campaign.latest_review.notes}</p>
          {failedChecks.length > 0 && (
            <ul>
              {failedChecks.map((check) => <li key={check.key}>{check.message}</li>)}
            </ul>
          )}
        </div>
      )}

      {(campaign.facebook_event_url || campaign.facebook_group_url || campaign.facebook_page_url) && (
        <div className="facebook-hub-links">
          {campaign.facebook_event_url && <a href={campaign.facebook_event_url} target="_blank" rel="noreferrer">Facebook Event</a>}
          {campaign.facebook_group_url && <a href={campaign.facebook_group_url} target="_blank" rel="noreferrer">Facebook Group</a>}
          {campaign.facebook_page_url && <a href={campaign.facebook_page_url} target="_blank" rel="noreferrer">Facebook Page</a>}
        </div>
      )}

      <div className="progress"><div style={{ width: `${campaign.progress_percent}%` }} /></div>
      <div className="metrics">
        <div><strong>{campaign.active_supporter_count.toLocaleString()}</strong><span><Users size={15} /> pledged ticket quantity</span></div>
        <div><strong>{money(campaign.committed_amount)}</strong><span>deposit and sponsor commitments</span></div>
        <div><strong>{campaign.progress_percent}%</strong><span>minimum demand reached</span></div>
      </div>

      <div className="review-summary">
        <strong><TicketCheck size={17} /> Attendance and ticket-price forecast</strong>
        <div className="metrics">
          <div><strong>{summary.expected_attendance.toLocaleString()}</strong><span><Users size={15} /> expected attendance</span></div>
          <div><strong>{summary.physical_expected_attendance.toLocaleString()}</strong><span>physical</span></div>
          <div><strong>{summary.virtual_expected_attendance.toLocaleString()}</strong><span><MonitorPlay size={15} /> virtual</span></div>
          <div><strong>{money(summary.projected_ticket_revenue)}</strong><span>projected ticket revenue</span></div>
          <div><strong>{money(summary.deposits_collected)}</strong><span>deposits collected</span></div>
          <div><strong>{money(summary.sponsor_commitments)}</strong><span>sponsor commitments</span></div>
          <div><strong>{money(summary.total_conditional_funding)}</strong><span><Banknote size={15} /> conditional funding only</span></div>
        </div>

        {summary.date_results.length > 0 && (
          <>
            <strong>Date voting</strong>
            <ul>
              {summary.date_results.map((result) => (
                <li key={result.option_id}>
                  {result.label || new Date(result.start_datetime).toLocaleString()}
                  {": "}
                  {result.expected_attendance} expected
                  {" ("}{result.physical_expected_attendance} physical,{" "}
                  {result.virtual_expected_attendance} virtual{")"}
                </li>
              ))}
            </ul>
          </>
        )}

        {summary.price_results.length > 0 && (
          <>
            <strong>Price voting</strong>
            <ul>
              {summary.price_results.map((result) => (
                <li key={result.option_id}>
                  {result.label || money(result.amount)}
                  {": "}
                  {result.expected_attendance} expected,{" "}
                  {money(result.projected_revenue)} projected revenue
                </li>
              ))}
            </ul>
          </>
        )}
        <small>
          Projected ticket revenue is a forecast. It is never added to deposits,
          sponsor commitments, or conditional funding.
        </small>
      </div>

      <div className="confirmation-row">
        <span className={campaign.artist_confirmed ? "confirmed" : "pending"}><CheckCircle2 size={17} /> Artist {campaign.artist_confirmed ? "confirmed" : "pending"}</span>
        <span className={campaign.venue_confirmed ? "confirmed" : "pending"}><CheckCircle2 size={17} /> Venue {campaign.venue_confirmed ? "confirmed" : "pending"}</span>
      </div>

      {["draft", "rejected"].includes(campaign.status) && campaign.can_manage && (
        <button className="primary" disabled={busy} onClick={runApprovalChecks}>
          {busy ? "Checking…" : "Run approval checks"}
        </button>
      )}

      {campaign.status === "approved" && campaign.can_manage && (
        <button className="primary" disabled={busy} onClick={launchApprovedCampaign}>
          {busy ? "Launching…" : "Start collecting support"}
        </button>
      )}

      {campaign.status === "pending_review" && !campaign.can_review_campaign && (
        <p className="message">Automatic checks require administrator review. The failed conditions are listed above.</p>
      )}

      {campaign.status === "pending_review" && campaign.can_review_campaign && (
        <div className="review-controls">
          <textarea
            placeholder="Administrator review notes"
            value={reviewNotes}
            onChange={(event) => setReviewNotes(event.target.value)}
          />
          <div>
            <button className="primary" disabled={busy} onClick={() => reviewCampaign("approve")}>
              Approve
            </button>
            <button className="secondary" disabled={busy} onClick={() => reviewCampaign("reject")}>
              Reject with notes
            </button>
          </div>
        </div>
      )}

      <SupporterPreferenceForm
        campaign={campaign}
        authenticated={authenticated}
        onSave={onPreference}
      />

      {["collecting", "target_reached", "threshold_reached"].includes(campaign.status) && (
        <>
          <form className="pledge-form" onSubmit={pledge}>
            <input placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} required />
            <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <input type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="Refundable deposit" />
            <button className="primary" disabled={busy}>{busy ? "Supporting…" : "Make this gig happen"}</button>
          </form>
          <button className="secondary" type="button" onClick={() => setShowSponsor((value) => !value)}>Support as a sponsor</button>
          {showSponsor && (
            <form className="sponsor-form" onSubmit={submitSponsor}>
              <input placeholder="Sponsor or company" value={sponsor.sponsor_name} onChange={(e) => setSponsor({ ...sponsor, sponsor_name: e.target.value })} required />
              <input placeholder="Contact name" value={sponsor.contact_name} onChange={(e) => setSponsor({ ...sponsor, contact_name: e.target.value })} required />
              <input type="email" placeholder="Contact email" value={sponsor.contact_email} onChange={(e) => setSponsor({ ...sponsor, contact_email: e.target.value })} required />
              <input type="number" min="1" step="0.01" value={sponsor.amount} onChange={(e) => setSponsor({ ...sponsor, amount: e.target.value })} required />
              <textarea placeholder="Requested sponsor benefits" value={sponsor.benefits_requested} onChange={(e) => setSponsor({ ...sponsor, benefits_requested: e.target.value })} />
              <button className="primary" disabled={busy}>Commit sponsorship</button>
            </form>
          )}
        </>
      )}

      {clientSecret && stripePromise && (
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <DepositPayment onSuccess={async () => {
            setClientSecret("");
            setMessage("Deposit received. You are helping make this gig happen.");
            await onReload();
          }} />
        </Elements>
      )}
      {clientSecret && !stripePromise && <p className="error">Set VITE_STRIPE_PUBLISHABLE_KEY to complete Stripe deposits.</p>}

      <FacebookIntegration campaign={campaign} onMessage={setMessage} />
      <small>Deposits are refundable when the campaign misses its target or cannot confirm the artist and venue under the published terms.</small>
      {message && <p className="message">{message}</p>}
    </article>
  );
}
