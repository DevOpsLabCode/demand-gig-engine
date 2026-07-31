/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Presents campaign status and progress, captures supporter/sponsor input, completes deposits, and exposes sharing integrations.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { FormEvent, useMemo, useState } from "react";
import { Elements } from "@stripe/react-stripe-js";
import { CalendarDays, CheckCircle2, MapPin, Share2, Users } from "lucide-react";
import type { Campaign, PledgeInput, PledgeResult, SponsorInput } from "../types";
import { stripePromise } from "../stripe";
import { DepositPayment } from "./DepositPayment";
import { FacebookIntegration } from "./FacebookIntegration";
import { trackMetaEvent } from "../meta";

/**
 * Receive one campaign plus callbacks for state transitions, commitments, sponsorships, and authoritative reloads.
 */
interface Props {
  campaign: Campaign;
  onLaunch: (slug: string) => Promise<void>;
  onPledge: (slug: string, data: PledgeInput) => Promise<PledgeResult>;
  onSponsor: (slug: string, data: SponsorInput) => Promise<void>;
  onReload: () => Promise<void>;
}

/**
 * Render lifecycle status, threshold metrics, confirmation state, pledge/sponsor forms, Stripe deposit completion, and social sharing.
 */
export function CampaignCard({ campaign, onLaunch, onPledge, onSponsor, onReload }: Props) {
  /**
   * Format server-supplied decimal strings in the campaign currency for readable progress and target values.
   */
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
  const [showSponsor, setShowSponsor] = useState(false);
  const [sponsor, setSponsor] = useState<SponsorInput>({
    sponsor_name: "",
    contact_name: "",
    contact_email: "",
    amount: "1000.00",
    benefits_requested: "",
  });

  /** Submit one idempotent supporter commitment and open Stripe only when the backend returns a client secret. */
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

  /** Validate and submit a sponsor commitment, then reset only the form fields after success. */
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

  /** Use the native share sheet when available, otherwise copy the public campaign URL to the clipboard. */
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
          <div className="meta"><span><MapPin size={16} /> {campaign.city}</span><span><CalendarDays size={16} /> Ends {new Date(campaign.deadline).toLocaleDateString()}</span></div>
        </div>
        <button className="icon-button" onClick={share} aria-label="Share campaign"><Share2 /></button>
      </div>

      <p>{campaign.pitch}</p>
      {(campaign.facebook_event_url || campaign.facebook_group_url || campaign.facebook_page_url) && (
        <div className="facebook-hub-links">
          {campaign.facebook_event_url && <a href={campaign.facebook_event_url} target="_blank" rel="noreferrer">Facebook Event</a>}
          {campaign.facebook_group_url && <a href={campaign.facebook_group_url} target="_blank" rel="noreferrer">Facebook Group</a>}
          {campaign.facebook_page_url && <a href={campaign.facebook_page_url} target="_blank" rel="noreferrer">Facebook Page</a>}
        </div>
      )}
      <div className="progress"><div style={{ width: `${campaign.progress_percent}%` }} /></div>
      <div className="metrics">
        <div><strong>{campaign.active_supporter_count.toLocaleString()}</strong><span><Users size={15} /> of {campaign.supporter_target.toLocaleString()} supporters</span></div>
        <div><strong>{money(campaign.committed_amount)}</strong><span>of {money(campaign.amount_target)} committed</span></div>
        <div><strong>{campaign.progress_percent}%</strong><span>minimum demand reached</span></div>
      </div>

      <div className="confirmation-row">
        <span className={campaign.artist_confirmed ? "confirmed" : "pending"}><CheckCircle2 size={17} /> Artist {campaign.artist_confirmed ? "confirmed" : "pending"}</span>
        <span className={campaign.venue_confirmed ? "confirmed" : "pending"}><CheckCircle2 size={17} /> Venue {campaign.venue_confirmed ? "confirmed" : "pending"}</span>
      </div>

      {campaign.status === "draft" ? (
        <button className="primary" onClick={() => onLaunch(campaign.slug)}>Launch campaign</button>
      ) : ["collecting", "target_reached"].includes(campaign.status) ? (
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
      ) : null}

      {clientSecret && stripePromise && (
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <DepositPayment onSuccess={async () => { setClientSecret(""); setMessage("Deposit received. You are helping make this gig happen."); await onReload(); }} />
        </Elements>
      )}
      {clientSecret && !stripePromise && <p className="error">Set VITE_STRIPE_PUBLISHABLE_KEY to complete Stripe deposits.</p>}

      <FacebookIntegration campaign={campaign} onMessage={setMessage} />
      <small>Deposits are refundable when the campaign misses its target or cannot confirm the artist and venue under the published terms.</small>
      {message && <p className="message">{message}</p>}
    </article>
  );
}
