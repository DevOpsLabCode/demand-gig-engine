/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Coordinates a discovery-first, role-aware campaign workspace with comfortable progressive disclosure.
 */

import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BadgeDollarSign,
  CalendarCheck2,
  Compass,
  LayoutDashboard,
  Menu,
  Music2,
  Plus,
  Search,
  Sparkles,
  Sprout,
  TicketCheck,
  Users,
  X,
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

type CampaignFilter = "discover" | "active" | "voting" | "mine";

const ACTIVE_STATUSES = new Set([
  "approved",
  "collecting",
  "target_reached",
  "threshold_reached",
  "feasibility_review",
  "conditionally_ready",
  "ready",
  "confirmed",
  "live",
]);

const VOTING_STATUSES = new Set([
  "approved",
  "collecting",
  "target_reached",
  "threshold_reached",
  "feasibility_review",
  "conditionally_ready",
  "ready",
]);

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

export default function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<CampaignFilter>("discover");
  const [showCreate, setShowCreate] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
        const pixelId =
          config.pixel_id || import.meta.env.VITE_META_PIXEL_ID || "";
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
    setShowCreate(false);
    requestAnimationFrame(() => scrollToSection("campaigns"));
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

  const filteredCampaigns = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return campaigns.filter((campaign) => {
      const matchesSearch =
        !normalizedQuery ||
        [
          campaign.title,
          campaign.artist_name,
          campaign.city,
          campaign.pitch,
        ].some((value) => value.toLowerCase().includes(normalizedQuery));

      if (!matchesSearch) return false;
      if (filter === "active") return ACTIVE_STATUSES.has(campaign.status);
      if (filter === "voting") return VOTING_STATUSES.has(campaign.status);
      if (filter === "mine") return campaign.can_manage;
      return true;
    });
  }, [campaigns, filter, query]);

  const expectedAttendance = campaigns.reduce(
    (total, campaign) =>
      total + campaign.preference_summary.expected_attendance,
    0,
  );
  const activeCampaigns = campaigns.filter((campaign) =>
    ACTIVE_STATUSES.has(campaign.status),
  ).length;

  return (
    <main aria-busy={authState === "loading"}>
      <header className="site-header">
        <nav className="topbar" aria-label="Primary navigation">
          <button
            className="brand-button"
            type="button"
            onClick={() => scrollToSection("top")}
            aria-label="Open Concert home"
          >
            <span className="brand-mark"><Music2 aria-hidden="true" /></span>
            <span>
              <strong>Open Concert</strong>
              <small>with VibesMeet</small>
            </span>
          </button>

          <div className={`nav-links ${mobileMenuOpen ? "is-open" : ""}`}>
            <button type="button" onClick={() => scrollToSection("campaigns")}>
              Discover
            </button>
            <button type="button" onClick={() => scrollToSection("how-it-works")}>
              How it works
            </button>
            {authenticated && (
              <button
                type="button"
                onClick={() => {
                  setShowCreate(true);
                  requestAnimationFrame(() => scrollToSection("create-campaign"));
                }}
              >
                Create
              </button>
            )}
          </div>

          <div className="nav-actions">
            {authenticated && (
              <button
                className="button primary compact"
                type="button"
                onClick={() => {
                  setShowCreate(true);
                  requestAnimationFrame(() => scrollToSection("create-campaign"));
                }}
              >
                <Plus size={17} aria-hidden="true" />
                Start a campaign
              </button>
            )}
            <button
              className="menu-button"
              type="button"
              aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((open) => !open)}
            >
              {mobileMenuOpen ? <X /> : <Menu />}
            </button>
          </div>
        </nav>

        <section className="hero-layout" id="top">
          <div className="hero-copy">
            <span className="eyebrow">
              <Sparkles size={15} aria-hidden="true" />
              Community-powered live events
            </span>
            <h1>Prove the audience before anyone takes the risk.</h1>
            <p>
              Vote on dates and prices, build verified demand, and turn a shared
              idea into a real physical or virtual performance.
            </p>
            <div className="hero-actions">
              <button
                className="button primary large"
                type="button"
                onClick={() => scrollToSection("campaigns")}
              >
                Explore campaigns
                <ArrowRight size={18} aria-hidden="true" />
              </button>
              {authenticated && (
                <button
                  className="button secondary large"
                  type="button"
                  onClick={() => {
                    setShowCreate(true);
                    requestAnimationFrame(() =>
                      scrollToSection("create-campaign"),
                    );
                  }}
                >
                  <Sprout size={18} aria-hidden="true" />
                  Plant a gig seed
                </button>
              )}
            </div>
            <div className="trust-row" aria-label="Platform highlights">
              <span><TicketCheck size={17} /> Date and price voting</span>
              <span><BadgeDollarSign size={17} /> Transparent thresholds</span>
              <span><Users size={17} /> Physical and virtual demand</span>
            </div>
          </div>

          <aside className="hero-account" aria-label="Account">
            <AuthPanel onAuthStateChange={setAuthState} />
          </aside>
        </section>

        <section className="hero-stats" aria-label="Campaign overview">
          <div>
            <strong>{campaigns.length}</strong>
            <span>campaign ideas</span>
          </div>
          <div>
            <strong>{activeCampaigns}</strong>
            <span>open for action</span>
          </div>
          <div>
            <strong>{expectedAttendance.toLocaleString()}</strong>
            <span>forecast attendees</span>
          </div>
        </section>
      </header>

      <section className="how-it-works" id="how-it-works">
        <div className="section-intro compact-intro">
          <span className="section-kicker">A safer event model</span>
          <h2>From idea to show, with evidence at every step.</h2>
        </div>
        <ol className="journey-grid">
          <li><span>1</span><Sprout /><strong>Plant the idea</strong><p>Name the artist, city, dates, prices, and minimum threshold.</p></li>
          <li><span>2</span><CalendarCheck2 /><strong>Measure demand</strong><p>Fans vote and estimate physical or virtual attendance.</p></li>
          <li><span>3</span><BadgeDollarSign /><strong>Reach viability</strong><p>Deposits and sponsorships remain separate from forecasts.</p></li>
          <li><span>4</span><Music2 /><strong>Confirm and produce</strong><p>Artist and venue discussions begin after demand is proven.</p></li>
        </ol>
      </section>

      <section className="workspace">
        {authenticated && (
          <div className="workspace-tools">
            <details className="utility-disclosure">
              <summary>
                <LayoutDashboard size={18} />
                Account and roles
              </summary>
              <RoleManager />
            </details>
          </div>
        )}

        {authenticated && showCreate && (
          <section
            className="create-workspace"
            id="create-campaign"
            aria-labelledby="create-heading"
          >
            <div className="workspace-heading">
              <div>
                <span className="section-kicker">Organizer workspace</span>
                <h2 id="create-heading">Create a campaign</h2>
                <p>Complete one comfortable step at a time. You can review everything before publishing.</p>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={() => setShowCreate(false)}
                aria-label="Close campaign creator"
              >
                <X />
              </button>
            </div>
            <CreateCampaignForm onCreate={create} />
          </section>
        )}

        <section id="campaigns" className="campaign-section">
          <div className="section-intro">
            <span className="section-kicker">Discover demand</span>
            <div className="section-heading-row">
              <div>
                <h2>Campaigns people want to make real</h2>
                <p>
                  Compare audience demand, proposed dates, acceptable prices,
                  and funding progress without exposing private supporter data.
                </p>
              </div>
              {authenticated && !showCreate && (
                <button
                  className="button secondary"
                  type="button"
                  onClick={() => {
                    setShowCreate(true);
                    requestAnimationFrame(() =>
                      scrollToSection("create-campaign"),
                    );
                  }}
                >
                  <Plus size={17} />
                  New campaign
                </button>
              )}
            </div>
          </div>

          <div className="discovery-toolbar" role="search">
            <label className="search-field">
              <Search size={19} aria-hidden="true" />
              <span className="sr-only">Search campaigns</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search artist, city, or campaign"
              />
            </label>
            <div className="filter-tabs" aria-label="Campaign filters">
              {([
                ["discover", "All"],
                ["active", "Active"],
                ["voting", "Open for voting"],
                ["mine", "My campaigns"],
              ] as [CampaignFilter, string][])
                .filter(([value]) => value !== "mine" || authenticated)
                .map(([value, label]) => (
                  <button
                    type="button"
                    key={value}
                    className={filter === value ? "is-active" : ""}
                    aria-pressed={filter === value}
                    onClick={() => setFilter(value)}
                  >
                    {value === "discover" && <Compass size={16} />}
                    {label}
                  </button>
                ))}
            </div>
          </div>

          {error && (
            <div className="notice error-notice" role="alert">
              <strong>Campaigns could not be loaded.</strong>
              <span>{error}. Confirm the Django API is available at http://localhost:8000.</span>
            </div>
          )}

          {filteredCampaigns.length > 0 ? (
            <div className="campaign-grid">
              {filteredCampaigns.map((campaign) => (
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
          ) : (
            <div className="empty-state">
              <Compass size={38} aria-hidden="true" />
              <h3>No campaigns match these filters.</h3>
              <p>Try a broader search or return to all campaigns.</p>
              <button
                className="button secondary"
                type="button"
                onClick={() => {
                  setQuery("");
                  setFilter("discover");
                }}
              >
                Clear filters
              </button>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
