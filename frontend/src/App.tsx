/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Coordinates public campaign discovery, authentication, roles, campaign approval, voting, pledges, and sponsorships.
 */

import { useEffect, useState } from "react";
import {
  ArrowRight,
  BadgeDollarSign,
  Building2,
  Music2,
  Sprout,
  Users,
} from "lucide-react";
import { api } from "./api";
import { CampaignCard } from "./components/CampaignCard";
import { CreateCampaignForm } from "./components/CreateCampaignForm";
import { AuthPanel, type AuthState } from "./components/AuthPanel";
import { RoleManager } from "./components/RoleManager";
import type {
  Campaign,
  CampaignCreate,
  PledgeInput,
  PledgeResult,
  SponsorInput,
  SupporterPreference,
  SupporterPreferenceInput,
} from "./types";
import { initMetaPixel } from "./meta";

export default function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [error, setError] = useState("");

  async function reload() {
    try {
      setCampaigns(await api.listCampaigns());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    }
  }

  useEffect(() => {
    void reload();
    void api
      .facebookConfig()
      .then((config) => {
        const pixelId = config.pixel_id || import.meta.env.VITE_META_PIXEL_ID || "";
        initMetaPixel(pixelId);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (authState !== "loading") {
      void reload();
    }
  }, [authState]);


  async function create(data: CampaignCreate) {
    const campaign = await api.createCampaign(data);
    setCampaigns((current) => [campaign, ...current]);
  }

  async function submitReview(slug: string) {
    const campaign = await api.submitCampaignForReview(slug);
    await reload();
    return campaign;
  }

  async function approve(slug: string, notes: string) {
    const campaign = await api.approveCampaign(slug, notes);
    await reload();
    return campaign;
  }

  async function reject(slug: string, notes: string) {
    const campaign = await api.rejectCampaign(slug, notes);
    await reload();
    return campaign;
  }

  async function launch(slug: string) {
    const campaign = await api.launchCampaign(slug);
    await reload();
    return campaign;
  }

  async function savePreference(
    slug: string,
    data: SupporterPreferenceInput,
  ): Promise<SupporterPreference> {
    const preference = await api.savePreference(slug, data);
    await reload();
    return preference;
  }

  async function pledge(slug: string, data: PledgeInput): Promise<PledgeResult> {
    const result = await api.pledge(slug, data);
    await reload();
    return result;
  }

  async function sponsor(slug: string, data: SponsorInput) {
    await api.sponsor(slug, data);
    await reload();
  }

  const authenticated = authState === "authenticated";

  return (
    <main aria-busy={authState === "loading"}>
      <header className={`hero ${authenticated ? "" : "auth-first-page"}`}>
        <nav>
          <div className="brand">
            <Music2 />
            Open Concert × VibesMeet
          </div>
          <span>Demand-driven events</span>
        </nav>

        <AuthPanel onAuthStateChange={setAuthState} />

        {authenticated && (
          <>
            <div className="hero-copy">
              <span className="eyebrow">Do not book first and hope.</span>
              <h1>
                Prove the audience.
                <br />
                Then make the gig happen.
              </h1>
              <p>
                Plant a seed, pass transparent approval checks, vote on dates
                and prices, gather real commitments, and convert verified demand
                into a live or virtual event.
              </p>
            </div>
            <div className="flow">
              <span><Sprout /> Plant seed</span>
              <ArrowRight />
              <span><Users /> Vote on demand</span>
              <ArrowRight />
              <span><BadgeDollarSign /> Reach target</span>
              <ArrowRight />
              <span><Building2 /> Confirm venue</span>
              <ArrowRight />
              <span><Music2 /> Produce gig</span>
            </div>
          </>
        )}
      </header>

      <section className="content">
        {authenticated && (
          <>
            <RoleManager />
            <CreateCampaignForm onCreate={create} />
          </>
        )}
        <div className="section-heading">
          <h2>Gig seeds</h2>
          <p>
            Campaign forecasts show physical and virtual attendance, date votes,
            price votes, and projected ticket revenue separately from deposits
            and sponsor commitments.
          </p>
        </div>
        {error && (
          <div className="panel error">
            {error}. Start the Django API at http://localhost:8000.
          </div>
        )}
        <div className="campaign-list">
          {campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              authenticated={authenticated}
              onSubmitReview={submitReview}
              onApprove={approve}
              onReject={reject}
              onLaunch={launch}
              onPreference={savePreference}
              onPledge={pledge}
              onSponsor={sponsor}
              onReload={reload}
            />
          ))}
        </div>
      </section>
    </main>
  );
}
