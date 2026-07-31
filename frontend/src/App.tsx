/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Coordinates the single-page application, campaign loading, authentication state, campaign creation, and selected-campaign views.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { useEffect, useState } from "react";
import { ArrowRight, BadgeDollarSign, Building2, Music2, Sprout, Users } from "lucide-react";
import { api } from "./api";
import { CampaignCard } from "./components/CampaignCard";
import { CreateCampaignForm } from "./components/CreateCampaignForm";
import { AuthPanel } from "./components/AuthPanel";
import type { Campaign, CampaignCreate, PledgeInput, PledgeResult, SponsorInput } from "./types";
import { initMetaPixel } from "./meta";

/**
 * Render the application shell and coordinate campaign loading, creation, launch, pledges, sponsorships, and integration initialization.
 */
export default function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState("");

  /** Refresh the campaign list and surface API connectivity errors without discarding the current page shell. */
  async function reload() {
    try {
      setCampaigns(await api.listCampaigns());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    }
  }

  // On first render, load current campaign state and initialize Meta Pixel only when the backend or build supplies a pixel ID.
  useEffect(() => {
    void reload();
    void api.facebookConfig().then((config) => {
      const pixelId = config.pixel_id || import.meta.env.VITE_META_PIXEL_ID || "";
      initMetaPixel(pixelId);
    }).catch(() => undefined);
  }, []);

  /** Persist a new campaign and prepend it to local state so the organizer sees it immediately. */
  async function create(data: CampaignCreate) {
    const campaign = await api.createCampaign(data);
    setCampaigns((current) => [campaign, ...current]);
  }

  /** Move a draft campaign into demand collection, then reload server-calculated status and progress. */
  async function launch(slug: string) {
    await api.launchCampaign(slug);
    await reload();
  }

  /** Submit an idempotent supporter commitment, refresh totals, and return any Stripe client secret. */
  async function pledge(slug: string, data: PledgeInput): Promise<PledgeResult> {
    const result = await api.pledge(slug, data);
    await reload();
    return result;
  }

  /** Record a sponsor commitment and refresh campaign funding progress from the authoritative API. */
  async function sponsor(slug: string, data: SponsorInput) {
    await api.sponsor(slug, data);
    await reload();
  }

  return (
    <main>
      <header className="hero">
        <nav><div className="brand"><Music2 /> Open Concert × VibesMeet</div><span>Demand-driven events</span></nav>
        <AuthPanel />
        <div className="hero-copy">
          <span className="eyebrow">Do not book first and hope.</span>
          <h1>Prove the audience.<br />Then make the gig happen.</h1>
          <p>Plant a seed, gather real commitments, unlock sponsors, confirm the artist and venue, and convert verified demand into a live event.</p>
        </div>
        <div className="flow">
          <span><Sprout /> Plant seed</span><ArrowRight /><span><Users /> Gather fans</span><ArrowRight /><span><BadgeDollarSign /> Reach target</span><ArrowRight /><span><Building2 /> Confirm venue</span><ArrowRight /><span><Music2 /> Produce gig</span>
        </div>
      </header>

      <section className="content">
        <CreateCampaignForm onCreate={create} />
        <div className="section-heading"><h2>Gig seeds</h2><p>Campaigns become events only after demand is proven.</p></div>
        {error && <div className="panel error">{error}. Start the Django API at http://localhost:8000.</div>}
        <div className="campaign-list">
          {campaigns.map((campaign) => <CampaignCard key={campaign.id} campaign={campaign} onLaunch={launch} onPledge={pledge} onSponsor={sponsor} onReload={reload} />)}
        </div>
      </section>
    </main>
  );
}
