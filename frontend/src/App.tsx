/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Coordinates authentication, multiple roles, campaign loading, creation, launch, pledges, and sponsorships.
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

  async function create(data: CampaignCreate) {
    const campaign = await api.createCampaign(data);
    setCampaigns((current) => [campaign, ...current]);
  }

  async function launch(slug: string) {
    await api.launchCampaign(slug);
    await reload();
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
          <span>{authenticated ? "Demand-driven events" : "Open Concert Network"}</span>
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
                Plant a seed, gather real commitments, unlock sponsors, confirm the artist and venue,
                and convert verified demand into a live event.
              </p>
            </div>
            <div className="flow">
              <span><Sprout /> Plant seed</span>
              <ArrowRight />
              <span><Users /> Gather fans</span>
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

      {authenticated && (
        <section className="content">
          <RoleManager />
          <CreateCampaignForm onCreate={create} />
          <div className="section-heading">
            <h2>Gig seeds</h2>
            <p>Campaigns become events only after demand is proven.</p>
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
                onLaunch={launch}
                onPledge={pledge}
                onSponsor={sponsor}
                onReload={reload}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
