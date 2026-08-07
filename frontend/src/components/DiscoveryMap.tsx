/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Visualizes Open Concert demand as an artistic, interactive U.S. live-music network without a heavyweight mapping dependency.
 */

import { Music2, Radio, Sparkles } from "lucide-react";
import type { Campaign } from "../types";

export interface CityMarker {
  city: string;
  state: string;
  x: number;
  y: number;
}

export const MAJOR_US_CITIES: CityMarker[] = [
  { city: "Seattle", state: "WA", x: 13, y: 17 },
  { city: "Portland", state: "OR", x: 12, y: 27 },
  { city: "San Francisco", state: "CA", x: 11, y: 48 },
  { city: "Los Angeles", state: "CA", x: 17, y: 68 },
  { city: "San Diego", state: "CA", x: 19, y: 76 },
  { city: "Las Vegas", state: "NV", x: 25, y: 59 },
  { city: "Phoenix", state: "AZ", x: 30, y: 70 },
  { city: "Salt Lake City", state: "UT", x: 31, y: 43 },
  { city: "Denver", state: "CO", x: 42, y: 48 },
  { city: "Dallas", state: "TX", x: 49, y: 72 },
  { city: "Austin", state: "TX", x: 47, y: 80 },
  { city: "Houston", state: "TX", x: 54, y: 82 },
  { city: "Minneapolis", state: "MN", x: 57, y: 30 },
  { city: "Chicago", state: "IL", x: 66, y: 40 },
  { city: "Nashville", state: "TN", x: 66, y: 61 },
  { city: "New Orleans", state: "LA", x: 59, y: 82 },
  { city: "Atlanta", state: "GA", x: 73, y: 67 },
  { city: "Miami", state: "FL", x: 84, y: 88 },
  { city: "Washington", state: "DC", x: 84, y: 51 },
  { city: "Philadelphia", state: "PA", x: 87, y: 43 },
  { city: "New York", state: "NY", x: 90, y: 36 },
  { city: "Boston", state: "MA", x: 94, y: 26 },
];

const CITY_ALIASES: Record<string, string> = {
  nyc: "New York",
  "new york city": "New York",
  brooklyn: "New York",
  manhattan: "New York",
  queens: "New York",
  "los angeles": "Los Angeles",
  la: "Los Angeles",
  sf: "San Francisco",
  dc: "Washington",
  "washington dc": "Washington",
};

const ROUTES: Array<[string, string]> = [
  ["Seattle", "Portland"],
  ["Portland", "San Francisco"],
  ["San Francisco", "Los Angeles"],
  ["Los Angeles", "San Diego"],
  ["Los Angeles", "Denver"],
  ["San Francisco", "Denver"],
  ["Seattle", "Denver"],
  ["Denver", "Minneapolis"],
  ["Denver", "Chicago"],
  ["Denver", "Dallas"],
  ["Los Angeles", "Austin"],
  ["Phoenix", "Austin"],
  ["Dallas", "Austin"],
  ["Austin", "Houston"],
  ["Houston", "New Orleans"],
  ["Dallas", "Nashville"],
  ["Chicago", "Nashville"],
  ["Minneapolis", "Chicago"],
  ["Nashville", "Atlanta"],
  ["Nashville", "Washington"],
  ["Atlanta", "Miami"],
  ["Atlanta", "Washington"],
  ["Chicago", "New York"],
  ["Washington", "Philadelphia"],
  ["Philadelphia", "New York"],
  ["New York", "Boston"],
  ["Nashville", "New York"],
  ["New Orleans", "Miami"],
];

export function inferState(city: string, explicitState?: string): string {
  if (explicitState?.trim()) return explicitState.trim().toUpperCase();
  const normalized = city.trim().toLowerCase();
  const canonical = CITY_ALIASES[normalized] ?? city.trim();
  return MAJOR_US_CITIES.find((entry) => entry.city.toLowerCase() === canonical.toLowerCase())?.state ?? "";
}

interface Props {
  campaigns: Campaign[];
  selectedCity: string;
  onSelectCity: (city: string, state: string) => void;
}

function cityLevel(supporters: number, campaignCount: number, progress: number) {
  const score = supporters + campaignCount * 80 + progress * 4;
  if (score >= 1000) return { label: "Very High", intensity: 4 };
  if (score >= 420) return { label: "High", intensity: 3 };
  if (score >= 120) return { label: "Rising", intensity: 2 };
  return { label: campaignCount ? "Emerging" : "Open city", intensity: 1 };
}

export function DiscoveryMap({ campaigns, selectedCity, onSelectCity }: Props) {
  const demand = new Map<string, { campaigns: number; supporters: number; progress: number }>();
  for (const campaign of campaigns) {
    const city = CITY_ALIASES[campaign.city.trim().toLowerCase()] ?? campaign.city.trim();
    const current = demand.get(city) ?? { campaigns: 0, supporters: 0, progress: 0 };
    current.campaigns += 1;
    current.supporters += campaign.preference_summary?.expected_attendance ?? campaign.active_supporter_count ?? 0;
    current.progress = Math.max(current.progress, campaign.progress_percent || 0);
    demand.set(city, current);
  }

  const markerByCity = new Map(MAJOR_US_CITIES.map((marker) => [marker.city, marker]));

  return (
    <section className="demand-map-card" aria-label="United States live demand map">
      <div className="map-card-heading">
        <div>
          <span className="map-kicker"><Radio size={14} /> Live demand network</span>
          <h2>Choose a city from the map</h2>
          <p>See proposed gigs, active demand, and confirmed shows city by city.</p>
        </div>
        <div className="map-legend" aria-label="Map legend">
          <span><i className="legend-dot demand" /> Very high</span>
          <span><i className="legend-dot active" /> High</span>
          <span><i className="legend-dot confirmed" /> Rising</span>
        </div>
      </div>

      <div className="map-perspective-shell">
        <div className="map-dawn-glow" aria-hidden="true" />
        <div className="map-star-field" aria-hidden="true" />
        <div className="map-music-particles" aria-hidden="true">
          <span>♪</span><span>♫</span><span>♪</span><span>♬</span><span>♫</span>
        </div>
        <div className="map-grid-plane" aria-hidden="true" />
        <div className="map-coast-shape" aria-hidden="true">
          <span className="map-city-light light-west" />
          <span className="map-city-light light-central" />
          <span className="map-city-light light-east" />
          <span className="map-city-light light-south" />
        </div>

        <svg className="map-route-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="routePurple" x1="0" x2="1">
              <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.26" />
              <stop offset="48%" stopColor="#f0abfc" stopOpacity="0.92" />
              <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.32" />
            </linearGradient>
            <linearGradient id="routeGold" x1="0" x2="1">
              <stop offset="0%" stopColor="#f8c86a" stopOpacity="0.18" />
              <stop offset="55%" stopColor="#ffd782" stopOpacity="0.82" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.2" />
            </linearGradient>
            <filter id="routeGlow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="0.7" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          {ROUTES.map(([fromName, toName], index) => {
            const from = markerByCity.get(fromName);
            const to = markerByCity.get(toName);
            if (!from || !to) return null;
            const middleX = (from.x + to.x) / 2;
            const middleY = Math.min(from.y, to.y) - Math.max(3, Math.abs(to.x - from.x) * 0.08);
            return (
              <path
                key={`${fromName}-${toName}`}
                d={`M ${from.x} ${from.y} Q ${middleX} ${middleY} ${to.x} ${to.y}`}
                className={`map-route route-${index % 4 === 0 ? "gold" : "violet"}`}
                filter="url(#routeGlow)"
              />
            );
          })}
        </svg>

        {MAJOR_US_CITIES.map((marker) => {
          const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0, progress: 0 };
          const active = selectedCity.toLowerCase() === marker.city.toLowerCase();
          const level = cityLevel(stats.supporters, stats.campaigns, stats.progress);
          return (
            <button
              key={`${marker.city}-${marker.state}`}
              type="button"
              className={`map-city-marker intensity-${level.intensity} ${active ? "is-selected" : ""} ${stats.campaigns ? "has-demand" : ""}`}
              style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
              onClick={() => onSelectCity(marker.city, marker.state)}
              aria-label={`${marker.city}, ${marker.state}: ${stats.campaigns} campaigns, ${level.label} demand`}
            >
              <span className="marker-aura" />
              <span className="marker-pulse" />
              <span className="marker-core"><Music2 size={level.intensity >= 3 ? 12 : 10} aria-hidden="true" /></span>
              <span className="marker-label">
                <strong>{marker.city}</strong>
                <small>{stats.campaigns ? `${level.label} · ${stats.campaigns} ${stats.campaigns === 1 ? "gig" : "gigs"}` : level.label}</small>
              </span>
              {stats.campaigns > 0 && <span className="marker-count">{stats.campaigns}</span>}
            </button>
          );
        })}

        <div className="map-floating-stage stage-west" aria-hidden="true"><Music2 /></div>
        <div className="map-floating-stage stage-south" aria-hidden="true"><Music2 /></div>
        <div className="map-floating-stage stage-east" aria-hidden="true"><Music2 /></div>

        <div className="map-network-badge">
          <Sparkles size={16} />
          <span>Demand lights the route</span>
        </div>
      </div>
    </section>
  );
}
