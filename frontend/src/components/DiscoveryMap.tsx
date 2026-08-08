/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Renders the approved Open Concert watercolor demand atlas while preserving accessible live city interactions.
 */

import { Music2 } from "lucide-react";
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

const FEATURED_LABELS = new Set([
  "Seattle",
  "San Francisco",
  "Denver",
  "Austin",
  "Nashville",
  "New York",
]);

const ROUTES: Array<[string, string]> = [
  ["Seattle", "San Francisco"],
  ["Seattle", "Denver"],
  ["San Francisco", "Denver"],
  ["San Francisco", "Austin"],
  ["Denver", "Austin"],
  ["Denver", "Nashville"],
  ["Austin", "Nashville"],
  ["Austin", "Houston"],
  ["Houston", "Nashville"],
  ["Nashville", "New York"],
  ["Nashville", "Atlanta"],
  ["Atlanta", "New York"],
  ["New York", "Boston"],
];

const USA_OUTLINE = [
  "M 8 17",
  "L 14 14 L 20 15 L 25 17 L 31 18 L 36 19",
  "L 41 17 L 48 19 L 54 20 L 59 24 L 64 24",
  "L 69 27 L 74 26 L 78 29 L 81 33 L 83 36",
  "L 88 38 L 91 42 L 90 46 L 93 50 L 91 55",
  "L 88 59 L 88 64 L 85 68 L 82 72 L 79 75",
  "L 81 79 L 83 85 L 86 91 L 83 90 L 80 85",
  "L 77 79 L 73 76 L 69 77 L 65 80 L 61 80",
  "L 58 84 L 53 86 L 49 83 L 44 83 L 39 81",
  "L 34 83 L 29 79 L 24 78 L 20 74 L 17 71",
  "L 15 65 L 12 61 L 11 55 L 9 50 L 10 44",
  "L 9 38 L 10 33 L 9 28 L 10 23 Z",
].join(" ");

const STATE_HINTS = [
  "M 18 19 C 20 34 20 51 23 72",
  "M 31 18 C 31 35 32 53 34 79",
  "M 45 19 C 45 37 45 57 48 81",
  "M 59 24 C 58 41 58 62 58 83",
  "M 72 27 C 70 43 71 59 69 76",
  "M 11 37 C 32 35 55 36 86 40",
  "M 10 52 C 34 50 62 52 90 55",
  "M 15 66 C 34 64 60 66 82 71",
];

const WATERCOLOR_VEINS = [
  "M 12 25 C 27 19 39 27 50 36 C 60 44 70 35 84 31",
  "M 11 40 C 27 33 40 43 52 51 C 64 59 75 49 90 44",
  "M 14 55 C 30 47 43 57 55 66 C 66 75 76 68 85 60",
  "M 20 70 C 34 63 48 72 60 79 C 69 84 76 80 81 74",
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

function FloatingIsland({ x, y, scale = 1, city = false }: { x: number; y: number; scale?: number; city?: boolean }) {
  return (
    <g className="atlas-v4-island" transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx="0" cy="0" rx="8" ry="2.2" className="atlas-v4-island-top" />
      <path d="M -7 0 C -5 4 -4 10 0 16 C 4 10 5 4 7 0 Z" className="atlas-v4-island-rock" />
      <path d="M -4.6 1 C -3 6 -2.2 11 -1.2 14" className="atlas-v4-island-fall" />
      <path d="M 3.7 1 C 2.9 5 2.6 8 2.2 11" className="atlas-v4-island-fall faint" />
      <path d="M -4 -1 C -2 -4 2 -4 4 -1" className="atlas-v4-island-grass" />
      <circle cx="-2.8" cy="-2.6" r="1.45" className="atlas-v4-tree" />
      <rect x="-3.05" y="-1.7" width=".5" height="2" rx=".2" className="atlas-v4-tree-trunk" />
      {city && (
        <g className="atlas-v4-island-city">
          <rect x="-.7" y="-6.2" width="1.35" height="5.7" rx=".2" />
          <rect x="1" y="-4.5" width="1.3" height="4.2" rx=".2" />
          <rect x="2.8" y="-7.1" width="1.15" height="6.7" rx=".18" />
          <path d="M 2.8 -7.1 L 3.4 -8.5 L 4 -7.1 Z" />
          <rect x="-2.3" y="-3.8" width="1" height="3.4" rx=".2" />
        </g>
      )}
    </g>
  );
}

function SurrealGuitar() {
  return (
    <g className="atlas-v4-guitar" transform="translate(73 28) rotate(8)">
      <path
        d="M 1 27 C -5 23 -5 16 -.2 12 C -4 8 -2 2 2 0 C 6 -2 9 1 8 5 C 8 8 5 10 4 12 C 10 11 13 15 12 20 C 11 25 7 29 3 34 C 1 37 1 42 0 47 C -2 43 -3 38 -1 33 C .1 30 2 28 1 27 Z"
        className="atlas-v4-guitar-body"
      />
      <path d="M 3 13 C 5 8 6 1 7 -8 C 8 -16 9 -24 11 -31" className="atlas-v4-guitar-neck" />
      <path d="M 10.2 -31 C 12 -34 14 -34 15 -32 C 14 -29 12 -27 10 -27" className="atlas-v4-guitar-head" />
      <path d="M 1 15 C 3 9 5 2 6 -8 C 7 -16 8 -23 10 -29" className="atlas-v4-guitar-string" />
      <path d="M 3 17 C 5 10 6 2 7 -7 C 8 -15 9 -22 11 -29" className="atlas-v4-guitar-string alt" />
      <path d="M 2 26 C 5 26 8 23 9 20 C 8 29 5 35 2 41 C .5 44 1 48 0 51" className="atlas-v4-guitar-melt" />
      <circle cx="3.7" cy="14.4" r="2.1" className="atlas-v4-guitar-hole" />
    </g>
  );
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
    <section className="demand-map-card atlas-v4" aria-label="United States live demand map">
      <div className="map-perspective-shell atlas-v4-shell">
        <svg className="atlas-v4-art" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="atlasV4Sky" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#f8f0ff" />
              <stop offset="38%" stopColor="#eadbff" />
              <stop offset="72%" stopColor="#ffe9dc" />
              <stop offset="100%" stopColor="#fff8ee" />
            </linearGradient>
            <linearGradient id="atlasV4Land" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#6c63c5" />
              <stop offset="34%" stopColor="#8a73cf" />
              <stop offset="66%" stopColor="#6c5daf" />
              <stop offset="100%" stopColor="#493b8b" />
            </linearGradient>
            <radialGradient id="atlasV4Glow">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="26%" stopColor="#f3ccff" stopOpacity=".98" />
              <stop offset="62%" stopColor="#9c55ff" stopOpacity=".62" />
              <stop offset="100%" stopColor="#8b4cff" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="atlasV4Route" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#9d57ff" stopOpacity=".1" />
              <stop offset="48%" stopColor="#ffefff" stopOpacity=".98" />
              <stop offset="78%" stopColor="#eaa8ff" stopOpacity=".85" />
              <stop offset="100%" stopColor="#9d57ff" stopOpacity=".08" />
            </linearGradient>
            <linearGradient id="atlasV4Gold" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f3a83b" stopOpacity=".08" />
              <stop offset="50%" stopColor="#ffe9ad" stopOpacity="1" />
              <stop offset="100%" stopColor="#f0a342" stopOpacity=".08" />
            </linearGradient>
            <linearGradient id="atlasV4Rock" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8570b5" />
              <stop offset="50%" stopColor="#68578f" />
              <stop offset="100%" stopColor="#3c315e" />
            </linearGradient>
            <linearGradient id="atlasV4Guitar" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#38256f" />
              <stop offset="42%" stopColor="#7451b6" />
              <stop offset="72%" stopColor="#e6a14b" />
              <stop offset="100%" stopColor="#5b2c8f" />
            </linearGradient>
            <filter id="atlasV4Watercolor" x="-20%" y="-20%" width="140%" height="140%">
              <feTurbulence type="fractalNoise" baseFrequency=".018 .035" numOctaves="3" seed="19" result="noise" />
              <feColorMatrix in="noise" type="saturate" values="0" result="mono" />
              <feBlend in="SourceGraphic" in2="mono" mode="soft-light" />
            </filter>
            <filter id="atlasV4SoftGlow" x="-80%" y="-80%" width="260%" height="260%">
              <feGaussianBlur stdDeviation=".8" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="atlasV4RouteGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation=".28" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <clipPath id="atlasV4Clip"><path d={USA_OUTLINE} /></clipPath>
          </defs>

          <rect width="100" height="100" fill="url(#atlasV4Sky)" />
          <circle cx="63" cy="14" r="6" className="atlas-v4-sun" />
          <circle cx="67" cy="13" r="5.4" className="atlas-v4-moon-cut" />

          <g className="atlas-v4-clouds">
            <ellipse cx="12" cy="9" rx="18" ry="8" />
            <ellipse cx="24" cy="2" rx="20" ry="7" />
            <ellipse cx="89" cy="8" rx="20" ry="9" />
            <ellipse cx="95" cy="82" rx="21" ry="10" />
            <ellipse cx="12" cy="86" rx="20" ry="11" />
          </g>

          <FloatingIsland x={48} y={9} scale={0.85} city />
          <FloatingIsland x={13} y={75} scale={0.58} />
          <FloatingIsland x={86} y={76} scale={0.64} />

          <path className="atlas-v4-land-shadow" d={USA_OUTLINE} />
          <path className="atlas-v4-land" d={USA_OUTLINE} fill="url(#atlasV4Land)" filter="url(#atlasV4Watercolor)" />

          <g clipPath="url(#atlasV4Clip)">
            <rect x="7" y="13" width="88" height="80" className="atlas-v4-wash" />
            <g className="atlas-v4-state-hints">
              {STATE_HINTS.map((path, index) => <path d={path} key={`state-${index}`} />)}
            </g>
            <g className="atlas-v4-veins">
              {WATERCOLOR_VEINS.map((path, index) => <path d={path} key={`vein-${index}`} />)}
            </g>
            <g className="atlas-v4-speckles">
              {Array.from({ length: 65 }, (_, index) => {
                const x = 12 + ((index * 17) % 76);
                const y = 20 + ((index * 29) % 61);
                const r = index % 5 === 0 ? .28 : index % 3 === 0 ? .2 : .12;
                return <circle key={`spark-${index}`} cx={x} cy={y} r={r} />;
              })}
            </g>
          </g>

          <g className="atlas-v4-routes" filter="url(#atlasV4RouteGlow)">
            {ROUTES.map(([fromName, toName], index) => {
              const from = markerByCity.get(fromName);
              const to = markerByCity.get(toName);
              if (!from || !to) return null;
              const fromLive = (demand.get(fromName)?.campaigns ?? 0) > 0;
              const toLive = (demand.get(toName)?.campaigns ?? 0) > 0;
              const selectedRoute = selectedCity === fromName || selectedCity === toName;
              const middleX = (from.x + to.x) / 2;
              const middleY = Math.min(from.y, to.y) - Math.max(3.5, Math.abs(to.x - from.x) * .12);
              const gold = selectedRoute || (fromLive && toLive) || index % 5 === 2;
              return (
                <path
                  key={`${fromName}-${toName}`}
                  d={`M ${from.x} ${from.y} Q ${middleX} ${middleY} ${to.x} ${to.y}`}
                  className={`atlas-v4-route ${fromLive || toLive ? "is-live" : ""} ${selectedRoute ? "is-selected" : ""}`}
                  stroke={gold ? "url(#atlasV4Gold)" : "url(#atlasV4Route)"}
                />
              );
            })}
          </g>

          <g className="atlas-v4-staff">
            <path d="M 4 72 C 22 91 42 91 62 82 C 78 75 91 78 100 88" />
            <path d="M 4 74 C 22 93 42 93 62 84 C 78 77 91 80 100 90" />
            <path d="M 4 76 C 22 95 42 95 62 86 C 78 79 91 82 100 92" />
            <text x="21" y="90">♪</text>
            <text x="55" y="87">♫</text>
            <text x="77" y="83">♪</text>
          </g>

          <g className="atlas-v4-skyline" transform="translate(78 27)">
            <rect x="0" y="6" width="1.6" height="8" />
            <rect x="2" y="3" width="1.6" height="11" />
            <rect x="4.2" y="7" width="1.4" height="7" />
            <rect x="6" y="1" width="1.8" height="13" />
            <path d="M 6 1 L 6.9 -2 L 7.8 1 Z" />
            <rect x="8.5" y="5" width="1.4" height="9" />
            <rect x="10.7" y="2.5" width="1.5" height="11.5" />
            <rect x="12.8" y="7" width="1.3" height="7" />
          </g>

          <SurrealGuitar />

          <g className="atlas-v4-birds">
            <path d="M 88 20 q 1 -1 2 0 q 1 -1 2 0" />
            <path d="M 91 23 q .7 -.7 1.4 0 q .7 -.7 1.4 0" />
          </g>
        </svg>

        {MAJOR_US_CITIES.map((marker) => {
          const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0, progress: 0 };
          const active = selectedCity.toLowerCase() === marker.city.toLowerCase();
          const level = cityLevel(stats.supporters, stats.campaigns, stats.progress);
          const featured = FEATURED_LABELS.has(marker.city);

          return (
            <button
              key={`${marker.city}-${marker.state}`}
              type="button"
              className={`map-city-marker atlas-v4-city intensity-${level.intensity} ${active ? "is-selected" : ""} ${stats.campaigns ? "has-demand" : ""}`}
              data-featured={featured ? "true" : "false"}
              style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
              onClick={() => onSelectCity(marker.city, marker.state)}
              aria-label={`${marker.city}, ${marker.state}: ${stats.campaigns} campaigns, ${level.label} demand`}
            >
              <span className="marker-aura" />
              <span className="marker-core"><Music2 size={9} aria-hidden="true" /></span>
              <span className="marker-label">
                <strong>{marker.city}</strong>
                <small>{stats.campaigns ? `${level.label} · ${stats.campaigns} ${stats.campaigns === 1 ? "gig" : "gigs"}` : level.label}</small>
              </span>
              {stats.campaigns > 0 && <span className="marker-count">{stats.campaigns}</span>}
            </button>
          );
        })}

        <div className="atlas-v4-title" aria-hidden="true">
          <strong>LIVE DEMAND ATLAS</strong>
          <span>Real fans. Real cities. Real music.</span>
        </div>
      </div>
    </section>
  );
}
