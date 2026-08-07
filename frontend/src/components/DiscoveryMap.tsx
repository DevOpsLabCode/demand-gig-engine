/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Visualizes Open Concert demand as an artistic, interactive U.S. live-music atlas without a heavyweight mapping dependency.
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

/*
 * An intentionally illustrated continental outline. It is not a survey map; it is
 * a concert atlas whose normalized 0-100 coordinate system also anchors the live
 * city controls above it.
 */
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

const STATE_LINES = [
  "M 15 18 L 16 31 L 13 45 L 17 58 L 18 70",
  "M 20 16 L 22 29 L 24 43 L 25 59 L 29 77",
  "M 29 17 L 30 31 L 31 45 L 31 61 L 34 81",
  "M 37 18 L 37 31 L 38 46 L 39 62 L 39 79",
  "M 45 18 L 45 31 L 45 48 L 46 64 L 48 81",
  "M 53 20 L 53 33 L 54 47 L 54 64 L 55 82",
  "M 61 23 L 61 35 L 62 47 L 61 61 L 60 79",
  "M 68 26 L 67 37 L 68 48 L 68 61 L 66 77",
  "M 75 27 L 74 37 L 76 46 L 75 58 L 72 74",
  "M 81 32 L 79 41 L 82 49 L 81 61 L 78 76",
  "M 10 32 C 27 30 43 30 60 32 C 70 33 79 35 88 38",
  "M 10 43 C 27 42 43 42 59 43 C 70 44 80 45 91 48",
  "M 10 54 C 25 53 41 54 56 55 C 68 56 78 58 87 60",
  "M 14 64 C 30 63 45 64 60 65 C 70 66 78 68 83 71",
  "M 20 73 C 34 71 49 72 62 73 C 69 73 74 74 78 77",
];

const CONTOURS = [
  "M 12 23 C 21 20 31 22 38 27 C 45 32 50 30 56 27",
  "M 13 29 C 22 26 30 28 37 34 C 43 39 50 37 57 33",
  "M 14 36 C 23 33 31 36 38 41 C 46 47 53 44 61 39",
  "M 16 47 C 24 43 31 46 39 52 C 48 59 55 56 63 51",
  "M 18 57 C 27 52 36 56 44 62 C 52 69 61 67 69 61",
  "M 22 67 C 32 62 41 66 49 72 C 57 78 66 75 74 69",
  "M 34 25 C 40 22 48 24 53 29 C 59 35 65 34 72 30",
  "M 46 37 C 52 33 59 35 64 40 C 70 46 77 45 83 41",
  "M 50 52 C 57 48 64 50 70 55 C 76 61 81 60 86 56",
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
    <section className="demand-map-card atlas-v2" aria-label="United States live demand map">
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

      <div className="map-perspective-shell atlas-v2-shell">
        <div className="map-dawn-glow" aria-hidden="true" />
        <div className="map-star-field" aria-hidden="true" />
        <div className="atlas-aurora atlas-aurora-west" aria-hidden="true" />
        <div className="atlas-aurora atlas-aurora-east" aria-hidden="true" />

        <svg
          className="map-atlas-art"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="atlasLand" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#fffef7" />
              <stop offset="48%" stopColor="#eceae0" />
              <stop offset="100%" stopColor="#d3d0c4" />
            </linearGradient>
            <linearGradient id="atlasRouteViolet" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#7657ff" stopOpacity="0.18" />
              <stop offset="48%" stopColor="#a58cff" stopOpacity="0.98" />
              <stop offset="100%" stopColor="#6b46ff" stopOpacity="0.28" />
            </linearGradient>
            <linearGradient id="atlasRouteGold" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f3b63f" stopOpacity="0.16" />
              <stop offset="52%" stopColor="#ffd987" stopOpacity="1" />
              <stop offset="100%" stopColor="#f3b63f" stopOpacity="0.24" />
            </linearGradient>
            <pattern id="atlasGrain" width="3.5" height="3.5" patternUnits="userSpaceOnUse">
              <circle cx="0.8" cy="0.8" r="0.08" fill="#111216" opacity="0.22" />
              <circle cx="2.6" cy="2.1" r="0.06" fill="#111216" opacity="0.16" />
            </pattern>
            <filter id="atlasLandShadow" x="-20%" y="-20%" width="140%" height="150%">
              <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#000000" floodOpacity="0.46" />
            </filter>
            <filter id="atlasRouteGlow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="0.42" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <clipPath id="atlasUsClip"><path d={USA_OUTLINE} /></clipPath>
          </defs>

          <path className="atlas-land-halo" d={USA_OUTLINE} />
          <path className="atlas-land" d={USA_OUTLINE} fill="url(#atlasLand)" filter="url(#atlasLandShadow)" />

          <g clipPath="url(#atlasUsClip)">
            <rect className="atlas-grain" x="5" y="10" width="92" height="82" fill="url(#atlasGrain)" />
            <g className="atlas-contours">
              {CONTOURS.map((path, index) => <path d={path} key={`contour-${index}`} />)}
            </g>
            <g className="atlas-state-lines">
              {STATE_LINES.map((path, index) => <path d={path} key={`state-${index}`} />)}
            </g>
            <path className="atlas-river" d="M 58 28 C 55 38 58 47 56 55 C 54 63 57 70 58 82" />
            <path className="atlas-river-secondary" d="M 45 37 C 49 43 51 47 56 53" />
            <ellipse className="atlas-lake" cx="65" cy="31" rx="3.2" ry="1.2" />
            <ellipse className="atlas-lake" cx="70" cy="32.5" rx="2.7" ry="1.05" />
            <ellipse className="atlas-lake" cx="73.6" cy="30" rx="2.3" ry="0.9" />
            <ellipse className="atlas-lake" cx="76.5" cy="33.4" rx="1.7" ry="0.72" />
          </g>

          <g className="atlas-city-halos">
            {MAJOR_US_CITIES.map((marker) => {
              const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0, progress: 0 };
              const level = cityLevel(stats.supporters, stats.campaigns, stats.progress);
              return (
                <circle
                  key={`halo-${marker.city}`}
                  cx={marker.x}
                  cy={marker.y}
                  r={level.intensity >= 4 ? 3.4 : level.intensity >= 3 ? 2.7 : level.intensity >= 2 ? 2.1 : 1.15}
                  className={`atlas-city-halo intensity-${level.intensity} ${stats.campaigns ? "has-demand" : ""}`}
                />
              );
            })}
          </g>

          <g className="atlas-routes" filter="url(#atlasRouteGlow)">
            {ROUTES.map(([fromName, toName], index) => {
              const from = markerByCity.get(fromName);
              const to = markerByCity.get(toName);
              if (!from || !to) return null;
              const middleX = (from.x + to.x) / 2;
              const middleY = Math.min(from.y, to.y) - Math.max(3, Math.abs(to.x - from.x) * 0.08);
              const fromLive = (demand.get(fromName)?.campaigns ?? 0) > 0;
              const toLive = (demand.get(toName)?.campaigns ?? 0) > 0;
              const selectedRoute = selectedCity === fromName || selectedCity === toName;
              const gold = selectedRoute || (fromLive && toLive) || index % 7 === 0;
              return (
                <path
                  key={`${fromName}-${toName}`}
                  d={`M ${from.x} ${from.y} Q ${middleX} ${middleY} ${to.x} ${to.y}`}
                  className={`atlas-route ${gold ? "route-gold" : "route-violet"} ${fromLive || toLive ? "is-live" : ""}`}
                  stroke={gold ? "url(#atlasRouteGold)" : "url(#atlasRouteViolet)"}
                />
              );
            })}
          </g>

          <g className="atlas-sound-lines">
            <path d="M 8 84 C 27 92 45 91 61 87" />
            <path d="M 18 10 C 33 5 50 7 64 13" />
            <path d="M 73 18 C 82 12 91 14 96 21" />
          </g>
        </svg>

        <div className="map-music-particles" aria-hidden="true">
          <span>♪</span><span>♫</span><span>♪</span><span>♬</span><span>♫</span>
        </div>

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

        <div className="atlas-title" aria-hidden="true">
          <span>OPEN CONCERT</span>
          <strong>LIVE DEMAND ATLAS</strong>
          <small>Every light starts with a listener.</small>
        </div>

        <div className="map-network-badge">
          <Sparkles size={16} />
          <span>Demand lights the route</span>
        </div>
      </div>
    </section>
  );
}
