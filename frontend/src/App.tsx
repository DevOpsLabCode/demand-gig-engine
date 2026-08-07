/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Provides the Build 13 map-first discovery experience, campaign workspace, and member profile flows.
 */

import { useEffect, useMemo, useState } from "react";
import {
  BadgeDollarSign,
  CalendarDays,
  CheckCircle2,
  Compass,
  Home,
  ListFilter,
  Map,
  MapPin,
  Menu,
  Music2,
  Pencil,
  Plus,
  Search,
  Sprout,
  TicketCheck,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { api } from "./api";
import { AuthPanel, type AuthState } from "./components/AuthPanel";
import { Build13Dashboard } from "./components/Build13Dashboard";
import { CampaignCard } from "./components/CampaignCard";
import { CreateCampaignForm } from "./components/CreateCampaignForm";
import { inferState, MAJOR_US_CITIES } from "./components/DiscoveryMap";
import { EditCampaignForm } from "./components/EditCampaignForm";
import { ProfileDrawer } from "./components/ProfileDrawer";
import type {
  AuthUser,
  Campaign,
  CampaignCreate,
  PledgeInput,
  PledgeResult,
  SponsorInput,
  SupporterPreference,
  SupporterPreferenceInput,
} from "./types";
import { initMetaPixel } from "./meta";

type CampaignFilter = "discover" | "active" | "voting" | "confirmed" | "mine";

const ACTIVE_STATUSES = new Set([
  "approved", "collecting", "target_reached", "threshold_reached", "feasibility_review",
  "conditionally_ready", "ready", "confirmed", "live",
]);
const VOTING_STATUSES = new Set([
  "approved", "collecting", "target_reached", "threshold_reached", "feasibility_review",
  "conditionally_ready", "ready",
]);
const CONFIRMED_STATUSES = new Set(["confirmed", "live", "completed"]);

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function normalizedCity(value: string) {
  return value.trim().toLowerCase();
}

export default function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<CampaignFilter>("discover");
  const [selectedState, setSelectedState] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  async function reload() {
    try {
      setCampaigns(await api.listCampaigns());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "API unavailable");
    }
  }

  async function refreshAuth() {
    try {
      const config = await api.authConfig();
      setAuthUser(config.user);
      setAuthState(config.authenticated ? "authenticated" : "anonymous");
      if (config.user?.state && !selectedState) setSelectedState(config.user.state);
      if (config.user?.city && !selectedCity) setSelectedCity(config.user.city);
    } catch {
      setAuthUser(null);
      setAuthState("anonymous");
    }
  }

  useEffect(() => {
    void reload();
    void refreshAuth();
    void api.facebookConfig().then((config) => {
      initMetaPixel(config.pixel_id || import.meta.env.VITE_META_PIXEL_ID || "");
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (authState !== "loading") void reload();
  }, [authState]);

  async function create(data: CampaignCreate) {
    const campaign = await api.createCampaign({
      ...data,
      state: data.state || selectedState,
    });
    setCampaigns((current) => [campaign, ...current]);
    setShowCreate(false);
    requestAnimationFrame(() => scrollToSection("campaigns"));
  }

  async function finishEdit() {
    await reload();
    setEditingCampaign(null);
    requestAnimationFrame(() => scrollToSection("campaigns"));
  }

  function openCreate() {
    if (!authUser || !authUser.email_verified) {
      setProfileOpen(true);
      return;
    }
    setEditingCampaign(null);
    setShowCreate(true);
    requestAnimationFrame(() => scrollToSection("create-campaign"));
  }

  function openEdit(campaign: Campaign) {
    setShowCreate(false);
    setEditingCampaign(campaign);
    requestAnimationFrame(() => scrollToSection("edit-campaign"));
  }

  async function submitReview(slug: string) { const result = await api.submitCampaignForReview(slug); await reload(); return result; }
  async function approve(slug: string, notes: string) { const result = await api.approveCampaign(slug, notes); await reload(); return result; }
  async function reject(slug: string, notes: string) { const result = await api.rejectCampaign(slug, notes); await reload(); return result; }
  async function launch(slug: string) { const result = await api.launchCampaign(slug); await reload(); return result; }
  async function savePreference(slug: string, data: SupporterPreferenceInput): Promise<SupporterPreference> { const result = await api.savePreference(slug, data); await reload(); return result; }
  async function pledge(slug: string, data: PledgeInput): Promise<PledgeResult> { const result = await api.pledge(slug, data); await reload(); return result; }
  async function sponsor(slug: string, data: SponsorInput) { await api.sponsor(slug, data); await reload(); }

  const authenticated = authState === "authenticated";

  const states = useMemo(() => {
    const values = new Set(MAJOR_US_CITIES.map((entry) => entry.state));
    campaigns.forEach((campaign) => {
      const value = inferState(campaign.city, campaign.state);
      if (value) values.add(value);
    });
    return [...values].sort();
  }, [campaigns]);

  const cities = useMemo(() => {
    const values = new Set<string>();
    MAJOR_US_CITIES.filter((entry) => !selectedState || entry.state === selectedState).forEach((entry) => values.add(entry.city));
    campaigns.forEach((campaign) => {
      const state = inferState(campaign.city, campaign.state);
      if (!selectedState || state === selectedState) values.add(campaign.city);
    });
    return [...values].sort((a, b) => a.localeCompare(b));
  }, [campaigns, selectedState]);

  const filteredCampaigns = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return campaigns.filter((campaign) => {
      const state = inferState(campaign.city, campaign.state);
      const matchesSearch = !normalizedQuery || [campaign.title, campaign.artist_name, campaign.city, state, campaign.pitch]
        .some((value) => value.toLowerCase().includes(normalizedQuery));
      if (!matchesSearch) return false;
      if (selectedState && state !== selectedState) return false;
      if (selectedCity && normalizedCity(campaign.city) !== normalizedCity(selectedCity)) return false;
      if (filter === "active") return ACTIVE_STATUSES.has(campaign.status);
      if (filter === "voting") return VOTING_STATUSES.has(campaign.status);
      if (filter === "confirmed") return CONFIRMED_STATUSES.has(campaign.status);
      if (filter === "mine") return campaign.can_manage;
      return true;
    });
  }, [campaigns, filter, query, selectedCity, selectedState]);

  function chooseCity(city: string, state: string) {
    setSelectedState(state);
    setSelectedCity(city);
  }

  function changeState(value: string) {
    setSelectedState(value);
    setSelectedCity("");
  }

  return (
    <main className="phase2-app build13-app" aria-busy={authState === "loading"}>
      <header className="phase2-header build13-header" id="top">
        <nav className="phase2-topbar" aria-label="Primary navigation">
          <button className="phase2-brand" type="button" onClick={() => scrollToSection("top")}>
            <span className="brand-mark"><Music2 aria-hidden="true" /></span>
            <span><strong>Open Concert</strong><small>with VibesMeet</small></span>
          </button>

          <div className={`phase2-nav-links ${mobileMenuOpen ? "is-open" : ""}`}>
            <button type="button" onClick={() => scrollToSection("discovery-map")}><Map size={17} /> Discover</button>
            <button type="button" onClick={() => scrollToSection("campaigns")}><Compass size={17} /> Gigs</button>
            <button type="button" onClick={() => scrollToSection("how-it-works")}><TicketCheck size={17} /> How it works</button>
            {authenticated && <button type="button" onClick={openCreate}><Plus size={17} /> Create gig</button>}
          </div>

          <div className="phase2-account-actions">
            {authenticated && (
              <button className="button primary compact desktop-create" type="button" onClick={openCreate}>
                <Plus size={16} /> Create gig
              </button>
            )}
            <button className="profile-tab-button" type="button" onClick={() => setProfileOpen(true)}>
              <span className="profile-tab-avatar">
                {authUser?.avatar_url ? <img src={authUser.avatar_url} alt="" /> : <UserRound />}
              </span>
              <span className="profile-tab-copy">
                <strong>{authUser?.display_name || "Sign in"}</strong>
                <small>{authUser ? (authUser.email_verified ? "Verified member" : "Verify email") : "Profile"}</small>
              </span>
              {authUser?.email_verified && <CheckCircle2 className="profile-verified-icon" size={16} />}
            </button>
            <button className="menu-button phase2-menu-button" type="button" onClick={() => setMobileMenuOpen((value) => !value)} aria-label="Toggle menu">
              {mobileMenuOpen ? <X /> : <Menu />}
            </button>
          </div>
        </nav>
      </header>

      <Build13Dashboard
        campaigns={campaigns}
        query={query}
        selectedState={selectedState}
        selectedCity={selectedCity}
        states={states}
        cities={cities}
        authenticated={authenticated}
        emailVerified={Boolean(authUser?.email_verified)}
        onQueryChange={setQuery}
        onStateChange={changeState}
        onCityChange={setSelectedCity}
        onSelectCity={chooseCity}
        onOpenProfile={() => setProfileOpen(true)}
        onOpenCreate={openCreate}
        onShowCampaigns={() => scrollToSection("campaigns")}
      />

      <section className="how-it-works phase2-how build13-how" id="how-it-works">
        <div className="section-intro compact-intro">
          <span className="section-kicker">Demand → viable gig</span>
          <h2>Find the city. Prove the audience. Build the show.</h2>
        </div>
        <ol className="journey-grid phase2-journey">
          <li><span>1</span><MapPin /><strong>Choose the city</strong><p>Explore local demand before anyone books a room or takes financial risk.</p></li>
          <li><span>2</span><Users /><strong>Build real demand</strong><p>Fans vote on dates, prices, physical attendance, and virtual attendance.</p></li>
          <li><span>3</span><BadgeDollarSign /><strong>Reach viability</strong><p>Thresholds, sponsorships, and refundable commitments show whether the gig can work.</p></li>
          <li><span>4</span><Music2 /><strong>Confirm the show</strong><p>Artists, venues, organizers, rentals, and sponsors connect after demand is proven.</p></li>
        </ol>
      </section>

      <section className="workspace phase2-workspace">
        {authenticated && editingCampaign && (
          <section className="create-workspace owner-edit-workspace" id="edit-campaign" aria-labelledby="edit-heading">
            <div className="workspace-heading">
              <div><span className="section-kicker">Owner workspace</span><h2 id="edit-heading">Edit campaign seed</h2><p>Update the seed without changing protected lifecycle, payment, vote, or confirmation records.</p></div>
              <button className="icon-button" type="button" onClick={() => setEditingCampaign(null)} aria-label="Close campaign editor"><X /></button>
            </div>
            <EditCampaignForm key={`${editingCampaign.slug}-${editingCampaign.status}`} campaign={editingCampaign} onSaved={finishEdit} onCancel={() => setEditingCampaign(null)} />
          </section>
        )}

        {authenticated && showCreate && (
          <section className="create-workspace" id="create-campaign" aria-labelledby="create-heading">
            <div className="workspace-heading">
              <div>
                <span className="section-kicker">Create in {selectedCity || "your city"}{selectedState ? `, ${selectedState}` : ""}</span>
                <h2 id="create-heading">Plant a gig seed</h2>
                <p>Email verification is required before Stage 2 public approval. City/state context is attached to the campaign.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setShowCreate(false)} aria-label="Close campaign creator"><X /></button>
            </div>
            <CreateCampaignForm onCreate={create} />
          </section>
        )}

        <section id="campaigns" className="campaign-section phase2-campaign-section">
          <div className="section-intro">
            <span className="section-kicker">{selectedCity ? `${selectedCity}${selectedState ? `, ${selectedState}` : ""}` : "All cities"}</span>
            <div className="section-heading-row">
              <div>
                <h2>{selectedCity ? `Gigs people want in ${selectedCity}` : "Gigs people want to make real"}</h2>
                <p>Search by artist or city, filter by lifecycle, and compare demand without exposing supporter private data.</p>
              </div>
              <button className="button secondary" type="button" onClick={openCreate}><Plus size={17} /> Create a gig</button>
            </div>
          </div>

          <div className="phase2-discovery-toolbar" role="search">
            <label className="search-field phase2-search-field">
              <Search size={19} aria-hidden="true" />
              <span className="sr-only">Search campaigns</span>
              <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Artist, city, genre idea, campaign…" />
            </label>
            <div className="phase2-location-filters">
              <label><span>State</span><select value={selectedState} onChange={(event) => changeState(event.target.value)}><option value="">All</option>{states.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label><span>City</span><select value={selectedCity} onChange={(event) => setSelectedCity(event.target.value)}><option value="">All</option>{cities.map((value) => <option key={value}>{value}</option>)}</select></label>
            </div>
            <div className="filter-tabs phase2-filter-tabs" aria-label="Campaign filters">
              {([
                ["discover", "All"], ["active", "Active"], ["voting", "Voting"], ["confirmed", "Confirmed"], ["mine", "Mine"],
              ] as [CampaignFilter, string][])
                .filter(([value]) => value !== "mine" || authenticated)
                .map(([value, label]) => (
                  <button type="button" key={value} className={filter === value ? "is-active" : ""} aria-pressed={filter === value} onClick={() => setFilter(value)}>
                    {value === "discover" && <ListFilter size={15} />}{label}
                  </button>
                ))}
            </div>
          </div>

          {error && <div className="notice error-notice" role="alert"><strong>Campaigns could not be loaded.</strong><span>{error}</span></div>}

          {filteredCampaigns.length > 0 ? (
            <div className="campaign-grid phase2-campaign-grid">
              {filteredCampaigns.map((campaign) => (
                <div className="campaign-card-shell" key={campaign.id}>
                  <div className="campaign-location-ribbon"><MapPin size={14} /> {campaign.city}{inferState(campaign.city, campaign.state) ? `, ${inferState(campaign.city, campaign.state)}` : ""}</div>
                  {campaign.can_manage && (
                    <div className="owner-card-toolbar">
                      <span>Owner controls · editable at any stage</span>
                      <button className="button secondary compact" type="button" onClick={() => openEdit(campaign)}><Pencil size={15} /> Edit seed</button>
                    </div>
                  )}
                  <CampaignCard
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
                </div>
              ))}
            </div>
          ) : (
            <div className="phase2-empty-state">
              <CalendarDays />
              <h3>No gigs match this view yet.</h3>
              <p>That is exactly when a community member can plant the first seed for a city.</p>
              <button className="button primary" type="button" onClick={openCreate}><Sprout size={17} /> Start the first one</button>
            </div>
          )}
        </section>
      </section>

      <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
        <button type="button" onClick={() => scrollToSection("top")}><Home /><span>Home</span></button>
        <button type="button" onClick={() => scrollToSection("discovery-map")}><Map /><span>Map</span></button>
        <button className="mobile-create-action" type="button" onClick={openCreate}><Plus /><span>Create</span></button>
        <button type="button" onClick={() => scrollToSection("campaigns")}><Compass /><span>Gigs</span></button>
        <button type="button" onClick={() => setProfileOpen(true)}><UserRound /><span>Profile</span></button>
      </nav>

      {authUser ? (
        <ProfileDrawer user={authUser} open={profileOpen} onClose={() => setProfileOpen(false)} onUserChange={setAuthUser} />
      ) : profileOpen ? (
        <div className="profile-drawer-layer" role="presentation" onMouseDown={() => setProfileOpen(false)}>
          <aside className="profile-drawer auth-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="profile-drawer-header">
              <div><span className="section-kicker">Open Concert account</span><h2>Sign in or join</h2></div>
              <button className="icon-button" type="button" onClick={() => setProfileOpen(false)} aria-label="Close account"><X /></button>
            </div>
            <AuthPanel onAuthStateChange={(state) => { setAuthState(state); void refreshAuth(); }} />
          </aside>
        </div>
      ) : null}
    </main>
  );
}
