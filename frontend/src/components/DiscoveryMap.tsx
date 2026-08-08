/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Renders the approved surreal watercolor Open Concert atlas as native SVG while preserving real city interactions.
 */

import type { Campaign } from "../types";

export interface CityMarker {
  city: string;
  state: string;
  x: number;
  y: number;
}

export const MAJOR_US_CITIES: CityMarker[] = [
  { city: "Seattle", state: "WA", x: 13, y: 18 },
  { city: "Portland", state: "OR", x: 12, y: 27 },
  { city: "San Francisco", state: "CA", x: 11, y: 49 },
  { city: "Los Angeles", state: "CA", x: 16, y: 68 },
  { city: "San Diego", state: "CA", x: 18, y: 76 },
  { city: "Las Vegas", state: "NV", x: 25, y: 60 },
  { city: "Phoenix", state: "AZ", x: 30, y: 70 },
  { city: "Salt Lake City", state: "UT", x: 31, y: 44 },
  { city: "Denver", state: "CO", x: 42, y: 49 },
  { city: "Dallas", state: "TX", x: 49, y: 72 },
  { city: "Austin", state: "TX", x: 47, y: 80 },
  { city: "Houston", state: "TX", x: 55, y: 81 },
  { city: "Minneapolis", state: "MN", x: 58, y: 31 },
  { city: "Chicago", state: "IL", x: 66, y: 42 },
  { city: "Nashville", state: "TN", x: 67, y: 61 },
  { city: "New Orleans", state: "LA", x: 59, y: 82 },
  { city: "Atlanta", state: "GA", x: 74, y: 67 },
  { city: "Miami", state: "FL", x: 84, y: 87 },
  { city: "Washington", state: "DC", x: 83, y: 52 },
  { city: "Philadelphia", state: "PA", x: 87, y: 45 },
  { city: "New York", state: "NY", x: 90, y: 38 },
  { city: "Boston", state: "MA", x: 94, y: 28 },
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

const PROMINENT_CITIES = new Set(["Seattle", "San Francisco", "Denver", "Austin", "Nashville", "New York"]);

const ROUTES: Array<[string, string]> = [
  ["Seattle", "San Francisco"],
  ["Seattle", "Denver"],
  ["San Francisco", "Los Angeles"],
  ["San Francisco", "Denver"],
  ["Los Angeles", "Austin"],
  ["Denver", "Austin"],
  ["Denver", "Chicago"],
  ["Denver", "Nashville"],
  ["Austin", "Houston"],
  ["Austin", "Nashville"],
  ["Houston", "New Orleans"],
  ["New Orleans", "Nashville"],
  ["Nashville", "Atlanta"],
  ["Nashville", "New York"],
  ["Atlanta", "Miami"],
  ["Chicago", "New York"],
  ["Washington", "New York"],
  ["New York", "Boston"],
];

const USA_OUTLINE = [
  "M 8 18",
  "L 14 15 L 20 17 L 26 18 L 32 20 L 38 18",
  "L 43 20 L 49 21 L 55 22 L 60 26 L 65 26",
  "L 70 29 L 75 28 L 79 31 L 82 35 L 84 39",
  "L 89 41 L 92 45 L 91 50 L 94 54 L 92 58",
  "L 89 62 L 89 67 L 86 70 L 83 74 L 80 77",
  "L 82 81 L 84 86 L 87 92 L 84 91 L 81 86",
  "L 78 81 L 74 78 L 70 79 L 66 82 L 61 82",
  "L 58 86 L 53 87 L 49 84 L 44 84 L 39 82",
  "L 34 84 L 29 80 L 24 79 L 20 75 L 17 72",
  "L 15 66 L 12 62 L 11 56 L 9 51 L 10 45",
  "L 9 39 L 10 34 L 9 29 L 10 23 Z",
].join(" ");

const STATE_LINES = [
  "M 18 21 C 19 36 20 52 23 73",
  "M 31 19 C 31 36 32 55 34 81",
  "M 45 20 C 45 38 45 58 48 84",
  "M 59 24 C 58 42 58 63 58 84",
  "M 72 29 C 70 45 71 61 69 78",
  "M 11 38 C 32 36 55 37 87 41",
  "M 10 53 C 35 51 63 53 91 56",
  "M 15 67 C 34 65 61 67 83 72",
];

const CONTOURS = [
  "M 14 29 C 27 24 38 30 48 37 C 58 44 68 36 81 33",
  "M 13 44 C 27 38 39 45 50 52 C 61 59 74 52 88 47",
  "M 16 60 C 30 54 42 60 53 68 C 64 75 74 70 83 64",
  "M 25 74 C 37 70 49 75 59 81 C 67 85 74 82 79 78",
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

function demandLevel(supporters: number, campaignCount: number, progress: number) {
  const score = supporters + campaignCount * 80 + progress * 4;
  if (score >= 1000) return { key: "very-high", label: "Very High" };
  if (score >= 420) return { key: "high", label: "High" };
  if (score >= 120) return { key: "rising", label: "Rising" };
  return { key: campaignCount ? "emerging" : "open", label: campaignCount ? "Emerging" : "Open city" };
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
    <section className="demand-map-card atlas-v6" aria-label="United States live demand map">
      <div className="atlas-v6-shell">
        <svg className="atlas-v6-art" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="atlasSky" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#fffaf4" />
              <stop offset="33%" stopColor="#f4eaff" />
              <stop offset="70%" stopColor="#eee7ff" />
              <stop offset="100%" stopColor="#fff5e9" />
            </linearGradient>
            <radialGradient id="atlasSun" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#fffbe9" stopOpacity="1" />
              <stop offset="45%" stopColor="#ffe7b4" stopOpacity=".75" />
              <stop offset="100%" stopColor="#ffe7b4" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="atlasLand" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#6d55d5" />
              <stop offset="35%" stopColor="#8f7ae2" />
              <stop offset="68%" stopColor="#7767d4" />
              <stop offset="100%" stopColor="#5647ad" />
            </linearGradient>
            <linearGradient id="atlasLandWash" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffffff" stopOpacity=".20" />
              <stop offset="55%" stopColor="#d8c9ff" stopOpacity=".09" />
              <stop offset="100%" stopColor="#43368d" stopOpacity=".16" />
            </linearGradient>
            <linearGradient id="routeViolet" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#d8c9ff" stopOpacity=".2" />
              <stop offset="50%" stopColor="#f0d9ff" stopOpacity=".95" />
              <stop offset="100%" stopColor="#a17dff" stopOpacity=".3" />
            </linearGradient>
            <linearGradient id="routeGold" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f5c95e" stopOpacity=".15" />
              <stop offset="50%" stopColor="#ffe5a3" stopOpacity="1" />
              <stop offset="100%" stopColor="#f0a73d" stopOpacity=".28" />
            </linearGradient>
            <linearGradient id="guitarGold" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#5a45bd" />
              <stop offset="42%" stopColor="#6d4bc5" />
              <stop offset="66%" stopColor="#d58f32" />
              <stop offset="100%" stopColor="#f1b44d" />
            </linearGradient>
            <filter id="atlasSoftGlow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation=".5" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="atlasLandShadow" x="-20%" y="-20%" width="140%" height="150%">
              <feDropShadow dx="0" dy="2.5" stdDeviation="2.2" floodColor="#372c73" floodOpacity=".22" />
            </filter>
            <clipPath id="atlasUsaClip"><path d={USA_OUTLINE} /></clipPath>
          </defs>

          <rect width="100" height="100" fill="url(#atlasSky)" />
          <circle cx="79" cy="13" r="19" fill="url(#atlasSun)" opacity=".72" />
          <path className="atlas-v6-cloud" d="M0 15 C13 8 22 13 31 11 C41 9 47 3 57 8 C65 12 72 5 83 9 C91 12 97 9 100 8 L100 0 L0 0 Z" />
          <path className="atlas-v6-cloud lower" d="M0 89 C13 82 25 88 35 85 C45 82 54 91 66 86 C76 82 87 89 100 83 L100 100 L0 100 Z" />

          <g className="atlas-v6-island island-main">
            <ellipse cx="50" cy="9" rx="8" ry="1.55" />
            <path d="M42 9 L45 16 L48 21 L50 29 L52 20 L56 14 L58 9 Z" />
            <path className="island-grass" d="M42 8.7 C46 7.5 54 7.5 58 8.7 C55 10 45 10 42 8.7 Z" />
            <path className="island-city" d="M46 8 V4 H47 V8 M48 8 V2 H49 V8 M50 8 V5 H51 V8 M52 8 V1 H53 V8 M54 8 V4 H55 V8" />
          </g>

          <g className="atlas-v6-island island-left">
            <ellipse cx="14" cy="79" rx="4.5" ry="1" />
            <path d="M9.5 79 L12 84 L14 89 L16 84 L18.5 79 Z" />
            <path className="island-grass" d="M9.5 78.8 C12 77.9 16 77.9 18.5 78.8 C16 80 12 80 9.5 78.8 Z" />
          </g>

          <g className="atlas-v6-island island-right">
            <ellipse cx="88" cy="80" rx="4.6" ry="1" />
            <path d="M83.4 80 L86 85 L88 90 L90 85 L92.6 80 Z" />
            <path className="island-grass" d="M83.4 79.8 C86 78.8 90 78.8 92.6 79.8 C90 81 86 81 83.4 79.8 Z" />
          </g>

          <path d={USA_OUTLINE} fill="url(#atlasLand)" filter="url(#atlasLandShadow)" className="atlas-v6-land" />
          <path d={USA_OUTLINE} fill="url(#atlasLandWash)" className="atlas-v6-land-wash" />

          <g clipPath="url(#atlasUsaClip)">
            <g className="atlas-v6-state-lines">
              {STATE_LINES.map((path, index) => <path key={`state-${index}`} d={path} />)}
            </g>
            <g className="atlas-v6-contours">
              {CONTOURS.map((path, index) => <path key={`contour-${index}`} d={path} />)}
            </g>
            {Array.from({ length: 34 }).map((_, index) => {
              const x = 10 + ((index * 17) % 82);
              const y = 24 + ((index * 29) % 57);
              const size = index % 5 === 0 ? .34 : .2;
              return <circle key={`spark-${index}`} cx={x} cy={y} r={size} className="atlas-v6-spark" />;
            })}
          </g>

          <g className="atlas-v6-routes" filter="url(#atlasSoftGlow)">
            {ROUTES.map(([fromName, toName]) => {
              const from = markerByCity.get(fromName);
              const to = markerByCity.get(toName);
              if (!from || !to) return null;
              const fromLive = (demand.get(fromName)?.campaigns ?? 0) > 0;
              const toLive = (demand.get(toName)?.campaigns ?? 0) > 0;
              const selected = selectedCity === fromName || selectedCity === toName;
              const hot = selected || (fromLive && toLive);
              const midX = (from.x + to.x) / 2;
              const midY = Math.min(from.y, to.y) - Math.max(3, Math.abs(to.x - from.x) * .09);
              return (
                <path
                  key={`${fromName}-${toName}`}
                  d={`M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`}
                  className={`atlas-v6-route ${fromLive || toLive ? "is-live" : ""} ${selected ? "is-selected" : ""}`}
                  stroke={hot ? "url(#routeGold)" : "url(#routeViolet)"}
                />
              );
            })}
          </g>

          <g className="atlas-v6-music" aria-hidden="true">
            <path d="M31 12 C43 18 56 13 68 21 C76 26 83 20 91 25" />
            <text x="33" y="14">♪</text><text x="60" y="20">♫</text><text x="79" y="23">♪</text>
            <path d="M31 87 C45 82 55 90 70 84 C80 80 88 83 95 78" />
            <text x="36" y="86">♫</text><text x="67" y="84">♪</text>
          </g>

          <g className="atlas-v6-skyline" aria-hidden="true">
            <path d="M76 35 V29 H78 V35 M79 35 V23 H81 V35 M82 35 V31 H84 V35 M85 35 V18 H87 V35 M88 35 V26 H90 V35 M91 35 V30 H93 V35" />
            <path d="M84.7 18 L86 13 L87.3 18" />
          </g>
          <path className="atlas-v6-birds" d="M89 22 q1 -1 2 0 q1 -1 2 0 M93 26 q.7 -.7 1.4 0 q.7 -.7 1.4 0" />
          <path className="atlas-v6-crescent" d="M74 13 A5 5 0 1 1 78 17 A4 4 0 1 0 74 13 Z" />

          <g className="atlas-v6-guitar" filter="url(#atlasSoftGlow)" aria-hidden="true">
            <path className="guitar-body" d="M78 25 C75 30 74 36 76 40 C72 42 70 47 71 51 C72 55 76 56 79 55 C78 60 76 64 77 69 C78 73 82 72 84 68 C87 62 87 54 85 49 C89 47 91 42 90 38 C89 34 86 32 84 33 C85 29 85 24 84 20 C83 17 80 19 78 25 Z" />
            <path className="guitar-inner" d="M80 29 C78 35 78 41 80 45 C77 48 76 53 78 56 C80 58 83 56 84 53 C85 48 83 44 82 41 C84 37 85 31 84 27 C83 24 81 25 80 29 Z" />
            <path className="guitar-neck" d="M82 28 C83 21 84 13 85 6 C85.3 3 86 1.5 87 1.2 C88 1 88.4 2.2 88 4 C86.5 11 85 19 84 29 Z" />
            <path className="guitar-string" d="M84 29 C85 21 86 12 87 3" />
            <ellipse className="guitar-hole" cx="82" cy="45" rx="2" ry="1.6" />
          </g>
        </svg>

        <div className="atlas-v6-hotspots" aria-label="Choose a city on the map">
          {MAJOR_US_CITIES.map((marker) => {
            const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0, progress: 0 };
            const active = selectedCity.trim().toLowerCase() === marker.city.toLowerCase();
            const level = demandLevel(stats.supporters, stats.campaigns, stats.progress);
            const prominent = PROMINENT_CITIES.has(marker.city);

            return (
              <button
                key={`${marker.city}-${marker.state}`}
                type="button"
                className={`atlas-v6-city is-${level.key} ${active ? "is-selected" : ""} ${stats.campaigns ? "has-demand" : ""}`}
                data-prominent={prominent ? "true" : "false"}
                style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
                onClick={() => onSelectCity(marker.city, marker.state)}
                aria-label={`${marker.city}, ${marker.state}: ${level.label}${stats.campaigns ? `, ${stats.campaigns} ${stats.campaigns === 1 ? "campaign" : "campaigns"}` : ""}`}
              >
                <span className="atlas-v6-city-aura" aria-hidden="true" />
                <span className="atlas-v6-city-core" aria-hidden="true" />
                <span className="atlas-v6-city-label">
                  <strong>{marker.city}</strong>
                  <small>{stats.campaigns ? level.label : prominent ? level.label : marker.state}</small>
                </span>
              </button>
            );
          })}
        </div>

        <div className="atlas-v6-title" aria-hidden="true">
          <strong>LIVE DEMAND ATLAS</strong>
          <span>Real fans. Real cities. Real music.</span>
        </div>
      </div>
    </section>
  );
}
