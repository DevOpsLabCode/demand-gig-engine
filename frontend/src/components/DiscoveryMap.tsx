/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Renders a calm, artistic Open Concert U.S. demand atlas with accessible interactive city controls.
 */

import { Music2, Sparkles } from "lucide-react";
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

const ANCHOR_CITIES = new Set([
  "Seattle",
  "San Francisco",
  "Los Angeles",
  "Denver",
  "Chicago",
  "Austin",
  "New York",
  "Miami",
]);

const ROUTES: Array<[string, string]> = [
  ["Seattle", "San Francisco"],
  ["San Francisco", "Los Angeles"],
  ["Los Angeles", "Denver"],
  ["Denver", "Chicago"],
  ["Chicago", "New York"],
  ["New York", "Boston"],
  ["Denver", "Austin"],
  ["Austin", "Houston"],
  ["Houston", "New Orleans"],
  ["New Orleans", "Atlanta"],
  ["Atlanta", "Miami"],
  ["Nashville", "Washington"],
  ["Washington", "New York"],
];

const USA_OUTLINE = [
  "M 8 15",
  "L 14 13 L 20 14 L 25 16 L 31 17 L 36 18",
  "L 41 16 L 48 18 L 54 19 L 59 23 L 64 23",
  "L 69 26 L 74 25 L 78 28 L 81 32 L 83 35",
  "L 88 37 L 91 41 L 90 45 L 93 49 L 91 54",
  "L 88 58 L 88 63 L 85 67 L 82 71 L 79 74",
  "L 81 78 L 83 84 L 86 90 L 83 89 L 80 84",
  "L 77 78 L 73 75 L 69 76 L 65 79 L 61 79",
  "L 58 83 L 53 85 L 49 82 L 44 82 L 39 80",
  "L 34 82 L 29 78 L 24 77 L 20 73 L 17 70",
  "L 15 64 L 12 60 L 11 54 L 9 49 L 10 43",
  "L 9 37 L 10 32 L 9 27 L 10 22 Z",
].join(" ");

const CARTOGRAPHY = [
  "M 18 18 C 20 34 20 50 23 72",
  "M 31 17 C 31 34 32 52 34 79",
  "M 45 18 C 45 36 45 56 48 81",
  "M 59 23 C 58 40 58 61 58 82",
  "M 72 26 C 70 42 71 58 69 75",
  "M 11 36 C 32 34 55 35 86 39",
  "M 10 51 C 34 49 62 51 90 54",
  "M 15 65 C 34 63 60 65 82 70",
];

const CONTOURS = [
  "M 14 27 C 27 22 38 28 48 35 C 58 42 68 34 80 31",
  "M 13 42 C 27 36 39 43 50 50 C 61 57 73 50 87 45",
  "M 16 58 C 30 52 42 58 53 66 C 63 73 73 68 82 62",
  "M 25 72 C 37 68 49 73 59 79 C 67 83 73 80 78 76",
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
  if (score >= 1000) return { label: "Very high", intensity: 4 };
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
    <section className="demand-map-card atlas-v3" aria-label="United States live demand map">
      <div className="map-perspective-shell atlas-v3-shell">
        <div className="atlas-v3-glow atlas-v3-glow-west" aria-hidden="true" />
        <div className="atlas-v3-glow atlas-v3-glow-east" aria-hidden="true" />

        <svg className="map-atlas-art atlas-v3-art" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="atlasV3Land" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#24262d" />
              <stop offset="52%" stopColor="#17191f" />
              <stop offset="100%" stopColor="#0d0f14" />
            </linearGradient>
            <linearGradient id="atlasV3Violet" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#7047ff" stopOpacity="0.08" />
              <stop offset="50%" stopColor="#9f87ff" stopOpacity="0.72" />
              <stop offset="100%" stopColor="#7047ff" stopOpacity="0.08" />
            </linearGradient>
            <linearGradient id="atlasV3Gold" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f2b744" stopOpacity="0.08" />
              <stop offset="50%" stopColor="#ffd67d" stopOpacity="0.88" />
              <stop offset="100%" stopColor="#f2b744" stopOpacity="0.08" />
            </linearGradient>
            <filter id="atlasV3LandGlow" x="-20%" y="-20%" width="140%" height="150%">
              <feDropShadow dx="0" dy="2" stdDeviation="2.2" floodColor="#000000" floodOpacity="0.62" />
              <feDropShadow dx="0" dy="0" stdDeviation="0.45" floodColor="#f7f4ec" floodOpacity="0.42" />
            </filter>
            <filter id="atlasV3RouteGlow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="0.25" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <clipPath id="atlasV3Clip"><path d={USA_OUTLINE} /></clipPath>
          </defs>

          <path className="atlas-v3-land" d={USA_OUTLINE} fill="url(#atlasV3Land)" filter="url(#atlasV3LandGlow)" />

          <g clipPath="url(#atlasV3Clip)">
            <g className="atlas-v3-contours">
              {CONTOURS.map((path, index) => <path d={path} key={`contour-${index}`} />)}
            </g>
            <g className="atlas-v3-cartography">
              {CARTOGRAPHY.map((path, index) => <path d={path} key={`cartography-${index}`} />)}
            </g>
            <path className="atlas-v3-river" d="M 58 29 C 55 39 58 48 56 57 C 54 66 57 73 58 82" />
            <ellipse className="atlas-v3-lake" cx="65" cy="31" rx="3.2" ry="1.15" />
            <ellipse className="atlas-v3-lake" cx="70" cy="32.4" rx="2.7" ry="1.0" />
            <ellipse className="atlas-v3-lake" cx="73.7" cy="30.2" rx="2.15" ry="0.85" />
            <ellipse className="atlas-v3-lake" cx="76.4" cy="33.3" rx="1.55" ry="0.68" />
          </g>

          <g className="atlas-v3-routes" filter="url(#atlasV3RouteGlow)">
            {ROUTES.map(([fromName, toName]) => {
              const from = markerByCity.get(fromName);
              const to = markerByCity.get(toName);
              if (!from || !to) return null;

              const fromLive = (demand.get(fromName)?.campaigns ?? 0) > 0;
              const toLive = (demand.get(toName)?.campaigns ?? 0) > 0;
              const selectedRoute = selectedCity === fromName || selectedCity === toName;
              const live = fromLive || toLive;
              const gold = selectedRoute || (fromLive && toLive);
              const middleX = (from.x + to.x) / 2;
              const middleY = Math.min(from.y, to.y) - Math.max(2.5, Math.abs(to.x - from.x) * 0.07);

              return (
                <path
                  key={`${fromName}-${toName}`}
                  d={`M ${from.x} ${from.y} Q ${middleX} ${middleY} ${to.x} ${to.y}`}
                  className={`atlas-v3-route ${live ? "is-live" : ""} ${selectedRoute ? "is-selected" : ""}`}
                  stroke={gold ? "url(#atlasV3Gold)" : "url(#atlasV3Violet)"}
                />
              );
            })}
          </g>
        </svg>

        {MAJOR_US_CITIES.map((marker) => {
          const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0, progress: 0 };
          const active = selectedCity.toLowerCase() === marker.city.toLowerCase();
          const level = cityLevel(stats.supporters, stats.campaigns, stats.progress);
          const anchor = ANCHOR_CITIES.has(marker.city);

          return (
            <button
              key={`${marker.city}-${marker.state}`}
              type="button"
              className={`map-city-marker atlas-v3-city intensity-${level.intensity} ${active ? "is-selected" : ""} ${stats.campaigns ? "has-demand" : ""}`}
              data-anchor={anchor ? "true" : "false"}
              style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
              onClick={() => onSelectCity(marker.city, marker.state)}
              aria-label={`${marker.city}, ${marker.state}: ${stats.campaigns} campaigns, ${level.label} demand`}
            >
              <span className="marker-aura" />
              <span className="marker-core"><Music2 size={10} aria-hidden="true" /></span>
              <span className="marker-label">
                <strong>{marker.city}</strong>
                <small>{stats.campaigns ? `${level.label} · ${stats.campaigns} ${stats.campaigns === 1 ? "gig" : "gigs"}` : marker.state}</small>
              </span>
              {stats.campaigns > 0 && <span className="marker-count">{stats.campaigns}</span>}
            </button>
          );
        })}

        <div className="atlas-v3-title" aria-hidden="true">
          <span>OPEN CONCERT</span>
          <strong>LIVE DEMAND ATLAS</strong>
          <small>Demand appears as people raise their hands.</small>
        </div>

        <div className="atlas-v3-key" aria-hidden="true">
          <span><i className="atlas-key-dot open" /> Open city</span>
          <span><i className="atlas-key-dot demand" /> Demand</span>
          <span><i className="atlas-key-dot hot" /> High demand</span>
        </div>

        <div className="map-network-badge atlas-v3-badge">
          <Sparkles size={14} />
          <span>Every signal starts with a listener</span>
        </div>
      </div>
    </section>
  );
}
