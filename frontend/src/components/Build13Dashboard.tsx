/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Build 13 visual discovery dashboard inspired by the approved Open Concert map concept.
 */

import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Flame,
  List,
  Map as MapIcon,
  MapPin,
  Music2,
  Search,
  SlidersHorizontal,
  Sparkles,
  Users,
} from "lucide-react";
import { DiscoveryMap, inferState, MAJOR_US_CITIES } from "./DiscoveryMap";
import type { Campaign } from "../types";

interface Props {
  campaigns: Campaign[];
  query: string;
  selectedState: string;
  selectedCity: string;
  states: string[];
  cities: string[];
  authenticated: boolean;
  emailVerified: boolean;
  onQueryChange: (value: string) => void;
  onStateChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onSelectCity: (city: string, state: string) => void;
  onOpenProfile: () => void;
  onOpenCreate: () => void;
  onShowCampaigns: () => void;
}

interface CityDemand {
  city: string;
  state: string;
  campaigns: number;
  supporters: number;
  expectedAttendance: number;
  active: number;
  score: number;
}

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

function demandLabel(score: number) {
  if (score >= 1200) return "Very High";
  if (score >= 500) return "High";
  if (score >= 180) return "Rising";
  return "Emerging";
}

function campaignDate(campaign: Campaign) {
  const value = campaign.proposed_date || campaign.date_options?.[0]?.start_datetime || campaign.deadline;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return { month: "TBD", day: "—" };
  return {
    month: date.toLocaleDateString("en-US", { month: "short" }).toUpperCase(),
    day: date.toLocaleDateString("en-US", { day: "2-digit" }),
  };
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function Build13Dashboard({
  campaigns,
  query,
  selectedState,
  selectedCity,
  states,
  cities,
  authenticated,
  emailVerified,
  onQueryChange,
  onStateChange,
  onCityChange,
  onSelectCity,
  onOpenProfile,
  onOpenCreate,
  onShowCampaigns,
}: Props) {
  const cityMap = new Map<string, CityDemand>();

  for (const marker of MAJOR_US_CITIES) {
    cityMap.set(marker.city.toLowerCase(), {
      city: marker.city,
      state: marker.state,
      campaigns: 0,
      supporters: 0,
      expectedAttendance: 0,
      active: 0,
      score: 0,
    });
  }

  for (const campaign of campaigns) {
    const key = campaign.city.trim().toLowerCase();
    const current = cityMap.get(key) ?? {
      city: campaign.city,
      state: inferState(campaign.city, campaign.state),
      campaigns: 0,
      supporters: 0,
      expectedAttendance: 0,
      active: 0,
      score: 0,
    };
    const expected = campaign.preference_summary?.expected_attendance ?? 0;
    const supporters = campaign.active_supporter_count ?? 0;
    current.campaigns += 1;
    current.supporters += supporters;
    current.expectedAttendance += expected;
    current.active += ACTIVE_STATUSES.has(campaign.status) ? 1 : 0;
    current.score += Math.max(expected, supporters) + campaign.progress_percent * 5 + (ACTIVE_STATUSES.has(campaign.status) ? 90 : 25);
    cityMap.set(key, current);
  }

  const rankedCities = [...cityMap.values()]
    .filter((city) => city.campaigns > 0)
    .sort((a, b) => b.score - a.score || b.campaigns - a.campaigns)
    .slice(0, 5);

  const fallbackCities = MAJOR_US_CITIES.slice(0, 5).map((marker, index) => ({
    city: marker.city,
    state: marker.state,
    campaigns: 0,
    supporters: 0,
    expectedAttendance: 0,
    active: 0,
    score: 150 - index * 20,
  }));

  const trendingCities = rankedCities.length ? rankedCities : fallbackCities;
  const maxScore = Math.max(...trendingCities.map((city) => city.score), 1);
  const activeCampaigns = campaigns.filter((campaign) => ACTIVE_STATUSES.has(campaign.status));
  const expectedAttendance = campaigns.reduce(
    (total, campaign) => total + (campaign.preference_summary?.expected_attendance ?? 0),
    0,
  );
  const supporterCount = campaigns.reduce((total, campaign) => total + (campaign.active_supporter_count ?? 0), 0);
  const networkCities = new Set(campaigns.map((campaign) => `${campaign.city}|${inferState(campaign.city, campaign.state)}`)).size;

  const featured = [...campaigns].sort((a, b) => {
    const activeDelta = Number(ACTIVE_STATUSES.has(b.status)) - Number(ACTIVE_STATUSES.has(a.status));
    if (activeDelta) return activeDelta;
    return (b.progress_percent || 0) - (a.progress_percent || 0)
      || (b.preference_summary?.expected_attendance ?? 0) - (a.preference_summary?.expected_attendance ?? 0);
  })[0];

  const events = [...campaigns]
    .sort((a, b) => {
      const activeDelta = Number(ACTIVE_STATUSES.has(b.status)) - Number(ACTIVE_STATUSES.has(a.status));
      if (activeDelta) return activeDelta;
      return (b.progress_percent || 0) - (a.progress_percent || 0);
    })
    .slice(0, 6);

  const featuredDate = featured ? campaignDate(featured) : null;

  return (
    <section className="build13-dashboard" id="discovery-map" data-build="13" aria-label="Open Concert Build 13 discovery dashboard">
      <aside className="build13-left-panel">
        <div className="build13-intro">
          <span className="build13-eyebrow"><Sparkles size={14} /> Live music, everywhere</span>
          <h1>Discover the sound of demand.</h1>
          <p>Explore verified fan demand, upcoming gigs, and venues across the U.S. Vote for your city, support artists, and help bring live music to life.</p>
        </div>

        <div className="build13-network-stats" aria-label="Network statistics">
          <span><strong>{compactNumber(campaigns.length)}</strong><small>Campaigns</small></span>
          <span><strong>{compactNumber(networkCities)}</strong><small>Cities</small></span>
          <span><strong>{compactNumber(Math.max(supporterCount, expectedAttendance))}</strong><small>Demand</small></span>
          <span><strong>{compactNumber(activeCampaigns.length)}</strong><small>Active</small></span>
        </div>

        <div className="build13-side-card build13-trending-card">
          <div className="build13-card-title"><span><Flame size={15} /> Trending demand</span></div>
          <div className="build13-trending-list">
            {trendingCities.map((city, index) => (
              <button
                type="button"
                key={`${city.city}-${city.state}`}
                onClick={() => onSelectCity(city.city, city.state)}
                className={selectedCity.toLowerCase() === city.city.toLowerCase() ? "is-active" : ""}
              >
                <b>{index + 1}</b>
                <span className="build13-trending-copy"><strong>{city.city}, {city.state}</strong><i><span style={{ width: `${Math.max(18, (city.score / maxScore) * 100)}%` }} /></i></span>
                <small>{demandLabel(city.score)}</small>
              </button>
            ))}
          </div>
          <button type="button" className="build13-text-action" onClick={onShowCampaigns}>View all trends <ArrowRight size={14} /></button>
        </div>

        <div className="build13-side-card build13-community-card">
          <div className="build13-card-title"><span><Users size={15} /> Community pulse</span></div>
          <p>{campaigns.length ? `Demand is forming across ${networkCities || 1} ${networkCities === 1 ? "city" : "cities"}.` : "The first city can start with one community member."}</p>
          <button type="button" className="build13-text-action" onClick={authenticated && !emailVerified ? onOpenProfile : onShowCampaigns}>
            {authenticated && !emailVerified ? "Verify email" : "See live demand"} <ArrowRight size={14} />
          </button>
        </div>
      </aside>

      <div className="build13-map-column">
        <div className="build13-map-toolbar">
          <label className="build13-search">
            <Search size={17} />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Search cities, artists, venues, genres…"
              type="search"
            />
          </label>
          <label className="build13-select">
            <span className="flag-dot">🇺🇸</span>
            <select value={selectedState} onChange={(event) => onStateChange(event.target.value)} aria-label="Choose state">
              <option value="">United States</option>
              {states.map((state) => <option value={state} key={state}>{state}</option>)}
            </select>
          </label>
          <label className="build13-select build13-city-select">
            <MapPin size={16} />
            <select value={selectedCity} onChange={(event) => onCityChange(event.target.value)} aria-label="Choose city">
              <option value="">Choose a city</option>
              {cities.map((city) => <option value={city} key={city}>{city}</option>)}
            </select>
          </label>
          <div className="build13-view-toggle" aria-label="Discovery view">
            <button type="button" className="is-active"><MapIcon size={16} /> Map view</button>
            <button type="button" onClick={onShowCampaigns}><List size={16} /> List view</button>
          </div>
        </div>

        <div className="build13-map-stage">
          <div className="build13-map-top-actions">
            <span className="build13-demand-pill"><Flame size={14} /> Demand</span>
            <button type="button" onClick={onShowCampaigns}><SlidersHorizontal size={15} /> Filters</button>
          </div>
          <DiscoveryMap campaigns={campaigns} selectedCity={selectedCity} onSelectCity={onSelectCity} />
        </div>
      </div>

      <aside className="build13-right-panel">
        <div className="build13-side-card build13-featured-card">
          <div className="build13-card-title"><span><Sparkles size={15} /> Featured gig</span></div>
          {featured ? (
            <>
              <div className="build13-feature-art" aria-hidden="true">
                <div className="build13-stage-lights" />
                <Music2 size={44} />
                {featuredDate && <span className="build13-feature-date"><small>{featuredDate.month}</small><b>{featuredDate.day}</b></span>}
              </div>
              <h3>{featured.title}</h3>
              <p>{featured.artist_name} · {featured.city}{inferState(featured.city, featured.state) ? `, ${inferState(featured.city, featured.state)}` : ""}</p>
              <div className="build13-feature-meta">
                <span><Users size={14} /> {(featured.preference_summary?.expected_attendance ?? featured.active_supporter_count ?? 0).toLocaleString()}</span>
                <span><CheckCircle2 size={14} /> {Math.round(featured.progress_percent || 0)}% to goal</span>
              </div>
              <button type="button" className="build13-primary-action" onClick={() => { onSelectCity(featured.city, inferState(featured.city, featured.state)); onShowCampaigns(); }}>
                View details <ArrowRight size={16} />
              </button>
            </>
          ) : (
            <div className="build13-empty-feature">
              <Music2 size={38} />
              <h3>Your city could be first.</h3>
              <p>Plant a gig seed and let the map light up as demand grows.</p>
              <button type="button" className="build13-primary-action" onClick={onOpenCreate}>Start a campaign <ArrowRight size={16} /></button>
            </div>
          )}
        </div>

        <div className="build13-side-card build13-rising-card">
          <div className="build13-card-title"><span><ArrowUpRight size={15} /> Top rising cities</span></div>
          <ol>
            {trendingCities.map((city, index) => (
              <li key={`${city.city}-${city.state}`}>
                <button type="button" onClick={() => onSelectCity(city.city, city.state)}>
                  <b>{index + 1}</b><span>{city.city}, {city.state}</span><strong>+{Math.max(8, Math.round((city.score / maxScore) * 89))}% ↑</strong>
                </button>
              </li>
            ))}
          </ol>
          <button type="button" className="build13-text-action" onClick={onShowCampaigns}>Explore all cities <ArrowRight size={14} /></button>
        </div>
      </aside>

      <div className="build13-events-strip">
        <div className="build13-events-heading">
          <span><CalendarDays size={15} /> Upcoming events near you</span>
          <button type="button" onClick={onShowCampaigns}>See all events <ArrowRight size={14} /></button>
        </div>
        <div className="build13-event-grid">
          {events.length ? events.map((campaign, index) => {
            const date = campaignDate(campaign);
            const demand = campaign.progress_percent >= 75 ? "Very high demand" : campaign.progress_percent >= 40 ? "High demand" : "Rising";
            return (
              <button
                type="button"
                className={`build13-event-card art-${(index % 6) + 1}`}
                key={campaign.id}
                onClick={() => { onSelectCity(campaign.city, inferState(campaign.city, campaign.state)); onShowCampaigns(); }}
              >
                <span className="build13-event-demand">{demand}</span>
                <span className="build13-event-date"><small>{date.month}</small><b>{date.day}</b></span>
                <span className="build13-event-copy">
                  <strong>{campaign.artist_name || campaign.title}</strong>
                  <small>{campaign.title}</small>
                  <em>{campaign.city}{inferState(campaign.city, campaign.state) ? `, ${inferState(campaign.city, campaign.state)}` : ""}</em>
                </span>
                <span className="build13-event-attendance"><Users size={13} /> {(campaign.preference_summary?.expected_attendance ?? campaign.active_supporter_count ?? 0).toLocaleString()}</span>
              </button>
            );
          }) : (
            <button type="button" className="build13-event-card build13-event-empty" onClick={onOpenCreate}>
              <span className="build13-event-demand">Open city</span>
              <span className="build13-event-copy"><strong>Plant the first gig seed</strong><small>Build demand before anyone takes the risk.</small></span>
              <ArrowUpRight />
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
