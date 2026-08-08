/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Renders the approved surreal watercolor Open Concert atlas as resilient native SVG with real city interactions.
 */

import type { Campaign } from "../types";

export interface CityMarker {
  city: string;
  state: string;
  x: number;
  y: number;
}

export const MAJOR_US_CITIES: CityMarker[] = [
  { city: "Seattle", state: "WA", x: 12, y: 20 },
  { city: "Portland", state: "OR", x: 11, y: 29 },
  { city: "San Francisco", state: "CA", x: 10, y: 50 },
  { city: "Los Angeles", state: "CA", x: 15, y: 69 },
  { city: "San Diego", state: "CA", x: 18, y: 76 },
  { city: "Las Vegas", state: "NV", x: 25, y: 60 },
  { city: "Phoenix", state: "AZ", x: 30, y: 70 },
  { city: "Salt Lake City", state: "UT", x: 31, y: 44 },
  { city: "Denver", state: "CO", x: 42, y: 49 },
  { city: "Dallas", state: "TX", x: 49, y: 72 },
  { city: "Austin", state: "TX", x: 48, y: 80 },
  { city: "Houston", state: "TX", x: 56, y: 81 },
  { city: "Minneapolis", state: "MN", x: 58, y: 31 },
  { city: "Chicago", state: "IL", x: 66, y: 42 },
  { city: "Nashville", state: "TN", x: 68, y: 62 },
  { city: "New Orleans", state: "LA", x: 60, y: 82 },
  { city: "Atlanta", state: "GA", x: 75, y: 67 },
  { city: "Miami", state: "FL", x: 86, y: 87 },
  { city: "Washington", state: "DC", x: 84, y: 52 },
  { city: "Philadelphia", state: "PA", x: 87, y: 45 },
  { city: "New York", state: "NY", x: 90, y: 40 },
  { city: "Boston", state: "MA", x: 94, y: 30 },
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
  "M 8 20",
  "L 14 17 L 20 18 L 26 20 L 32 21 L 38 19",
  "L 44 21 L 50 22 L 56 23 L 61 27 L 66 27",
  "L 71 30 L 76 29 L 80 32 L 83 36 L 85 40",
  "L 90 42 L 93 46 L 92 51 L 95 55 L 93 59",
  "L 90 63 L 90 67 L 87 71 L 84 75 L 81 78",
  "L 83 82 L 85 87 L 88 93 L 85 92 L 82 87",
  "L 79 82 L 75 79 L 71 80 L 67 83 L 62 83",
  "L 59 87 L 54 88 L 50 85 L 45 85 L 40 83",
  "L 35 85 L 30 81 L 25 80 L 21 76 L 18 73",
  "L 16 67 L 13 63 L 12 57 L 10 52 L 11 46",
  "L 10 40 L 11 35 L 10 30 L 11 24 Z",
].join(" ");

const STATE_LINES = [
  "M 18 22 C 19 37 20 53 23 74",
  "M 31 20 C 31 37 32 56 34 82",
  "M 45 21 C 45 39 45 59 48 85",
  "M 59 25 C 58 43 58 64 58 85",
  "M 72 30 C 70 46 71 62 69 79",
  "M 11 39 C 32 37 55 38 88 42",
  "M 10 54 C 35 52 64 54 92 57",
  "M 15 68 C 34 66 61 68 84 73",
];

const CONTOURS = [
  "M 14 30 C 27 25 38 31 49 38 C 59 45 69 37 82 34",
  "M 13 45 C 27 39 39 46 51 53 C 62 60 75 53 89 48",
  "M 16 61 C 30 55 42 61 54 69 C 65 76 75 71 84 65",
  "M 25 75 C 37 71 49 76 60 82 C 68 86 75 83 80 79",
];

const NETWORK_SPARKS: Array<[number, number, number]> = [
  [14, 30, 0.22], [17, 38, 0.16], [19, 55, 0.2], [23, 66, 0.17], [26, 34, 0.14],
  [28, 49, 0.2], [31, 62, 0.18], [35, 29, 0.17], [36, 57, 0.23], [39, 73, 0.16],
  [43, 35, 0.18], [44, 64, 0.22], [48, 55, 0.24], [50, 76, 0.21], [53, 31, 0.14],
  [56, 47, 0.23], [58, 69, 0.17], [61, 35, 0.2], [62, 57, 0.26], [64, 74, 0.18],
  [68, 33, 0.19], [70, 50, 0.22], [73, 59, 0.25], [76, 42, 0.19], [78, 70, 0.21],
  [82, 48, 0.25], [83, 60, 0.2], [87, 53, 0.17], [88, 70, 0.2], [91, 46, 0.17],
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
    <section className="demand-map-card atlas-v6 atlas-approved" aria-label="United States live demand map">
      <div className="atlas-v6-shell">
        <svg className="atlas-v6-art" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="atlasSky" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#fffaf4" />
              <stop offset="30%" stopColor="#f6eaff" />
              <stop offset="68%" stopColor="#eee7ff" />
              <stop offset="100%" stopColor="#fff2e5" />
            </linearGradient>
            <radialGradient id="atlasSun" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#fffde9" stopOpacity="1" />
              <stop offset="48%" stopColor="#ffe5ae" stopOpacity=".74" />
              <stop offset="100%" stopColor="#ffe5ae" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="atlasLand" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#5f4bc9" />
              <stop offset="28%" stopColor="#8a71dc" />
              <stop offset="58%" stopColor="#7e68d0" />
              <stop offset="100%" stopColor="#493a9c" />
            </linearGradient>
            <linearGradient id="atlasLandWash" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffffff" stopOpacity=".28" />
              <stop offset="48%" stopColor="#e8d8ff" stopOpacity=".08" />
              <stop offset="100%" stopColor="#2f256f" stopOpacity=".20" />
            </linearGradient>
            <linearGradient id="routeViolet" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#b89bff" stopOpacity=".12" />
              <stop offset="50%" stopColor="#f4e8ff" stopOpacity=".98" />
              <stop offset="100%" stopColor="#8a5fff" stopOpacity=".22" />
            </linearGradient>
            <linearGradient id="routeGold" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#eaa548" stopOpacity=".12" />
              <stop offset="50%" stopColor="#ffe7a1" stopOpacity="1" />
              <stop offset="100%" stopColor="#f3a334" stopOpacity=".24" />
            </linearGradient>
            <linearGradient id="guitarLiquid" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#43349e" />
              <stop offset="35%" stopColor="#6650c7" />
              <stop offset="63%" stopColor="#aa6fc9" />
              <stop offset="80%" stopColor="#e2a348" />
              <stop offset="100%" stopColor="#f4bf59" />
            </linearGradient>
            <radialGradient id="islandTop" cx="50%" cy="35%" r="70%">
              <stop offset="0%" stopColor="#b1a3cc" />
              <stop offset="55%" stopColor="#8d7bb0" />
              <stop offset="100%" stopColor="#675a8a" />
            </radialGradient>
            <filter id="watercolorLand" x="-15%" y="-18%" width="130%" height="136%">
              <feTurbulence type="fractalNoise" baseFrequency="0.018 0.04" numOctaves={3} seed={9} result="paperNoise" />
              <feColorMatrix in="paperNoise" type="saturate" values="0" result="grayNoise" />
              <feComponentTransfer in="grayNoise" result="softNoise">
                <feFuncA type="table" tableValues="0 .24" />
              </feComponentTransfer>
              <feBlend in="SourceGraphic" in2="softNoise" mode="soft-light" result="painted" />
              <feTurbulence type="fractalNoise" baseFrequency="0.008 0.02" numOctaves={2} seed={4} result="edgeNoise" />
              <feDisplacementMap in="painted" in2="edgeNoise" scale="0.5" xChannelSelector="R" yChannelSelector="G" result="warped" />
              <feDropShadow dx="0" dy="1.8" stdDeviation="1.4" floodColor="#3d307f" floodOpacity=".22" />
            </filter>
            <filter id="atlasSoftGlow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation=".75" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="islandShadow" x="-50%" y="-40%" width="200%" height="200%">
              <feDropShadow dx="0" dy="2" stdDeviation="1.3" floodColor="#49396c" floodOpacity=".25" />
            </filter>
            <clipPath id="atlasUsaClip"><path d={USA_OUTLINE} /></clipPath>
          </defs>

          <rect width="100" height="100" fill="url(#atlasSky)" />
          <circle cx="79" cy="13" r="20" fill="url(#atlasSun)" opacity=".64" />
          <path className="atlas-v6-cloud" d="M0 15 C13 6 22 13 31 10 C41 7 47 2 58 8 C67 12 73 4 84 8 C92 11 98 8 100 7 L100 0 L0 0 Z" />
          <path className="atlas-v6-cloud lower" d="M0 90 C14 82 25 89 36 85 C47 81 56 92 67 86 C78 81 88 90 100 82 L100 100 L0 100 Z" />

          <g className="atlas-v6-island island-main" filter="url(#islandShadow)">
            <ellipse cx="49" cy="10" rx="8.7" ry="1.6" fill="url(#islandTop)" />
            <path className="island-rock" d="M40.3 10 C42 14 44 18 46 24 C47.4 27.8 48.2 31 49.2 34 C50 28 51.2 25 52 20 C54 16 56.8 13 57.7 10 Z" />
            <path className="island-grass" d="M40.3 9.6 C43.5 8.1 54.3 8.1 57.7 9.6 C55.4 11.2 42.7 11.2 40.3 9.6 Z" />
            <path className="island-city" d="M44 9 V5 H45.2 V9 M46 9 V3 H47.2 V9 M48 9 V6 H49.1 V9 M50 9 V1.5 H51.1 V9 M52 9 V4 H53.2 V9 M54 9 V2.8 H55.2 V9" />
            <path className="island-tree" d="M42.5 9 V6.4 M41.7 7 C42.4 5.6 43.3 5.6 44 7 M56 9 V6.6 M55.2 7.2 C55.9 5.8 56.9 5.8 57.6 7.2" />
          </g>

          <g className="atlas-v6-island island-left" filter="url(#islandShadow)">
            <ellipse cx="13" cy="80" rx="4.8" ry="1" fill="url(#islandTop)" />
            <path className="island-rock" d="M8.2 80 L10.6 84.2 L13 90 L15.2 85 L17.8 80 Z" />
            <path className="island-grass" d="M8.2 79.7 C10.5 78.5 15.4 78.5 17.8 79.7 C15.6 80.9 10.5 80.9 8.2 79.7 Z" />
            <path className="island-tree" d="M12.6 79 V75.8 M10.5 79 V77 M9.8 77.5 C10.5 75.8 11.2 75.8 11.8 77.5 M11.6 76.7 C12.5 74.7 13.7 74.7 14.5 76.7" />
          </g>

          <g className="atlas-v6-island island-right" filter="url(#islandShadow)">
            <ellipse cx="90" cy="81" rx="4.9" ry="1" fill="url(#islandTop)" />
            <path className="island-rock" d="M85.1 81 L87.7 85.6 L90 91 L92.1 85.2 L94.9 81 Z" />
            <path className="island-grass" d="M85.1 80.7 C87.5 79.4 92.5 79.4 94.9 80.7 C92.8 81.9 87.4 81.9 85.1 80.7 Z" />
            <path className="island-tree" d="M90.1 80 V76.7 M88 80 V78 M87.4 78.4 C88 76.9 88.9 76.9 89.6 78.4 M89.2 77.6 C90 75.7 91.2 75.7 92 77.6" />
          </g>

          <path d={USA_OUTLINE} fill="url(#atlasLand)" filter="url(#watercolorLand)" className="atlas-v6-land" />
          <path d={USA_OUTLINE} fill="url(#atlasLandWash)" className="atlas-v6-land-wash" />

          <g clipPath="url(#atlasUsaClip)">
            <g className="atlas-v6-state-lines">
              {STATE_LINES.map((path, index) => <path d={path} key={`state-${index}`} />)}
            </g>
            <g className="atlas-v6-contours">
              {CONTOURS.map((path, index) => <path d={path} key={`contour-${index}`} />)}
            </g>
            {NETWORK_SPARKS.map(([x, y, r], index) => (
              <circle key={`spark-${index}`} className="atlas-v6-spark" cx={x} cy={y} r={r} />
            ))}
          </g>

          <g className="atlas-v6-routes" filter="url(#atlasSoftGlow)">
            {ROUTES.map(([fromName, toName], index) => {
              const from = markerByCity.get(fromName);
              const to = markerByCity.get(toName);
              if (!from || !to) return null;
              const fromLive = (demand.get(fromName)?.campaigns ?? 0) > 0;
              const toLive = (demand.get(toName)?.campaigns ?? 0) > 0;
              const selectedRoute = selectedCity === fromName || selectedCity === toName;
              const gold = selectedRoute || (fromLive && toLive) || index % 4 === 1;
              const midX = (from.x + to.x) / 2;
              const bend = Math.max(2.8, Math.abs(to.x - from.x) * 0.08);
              const midY = Math.min(from.y, to.y) - bend;
              return (
                <path
                  key={`${fromName}-${toName}`}
                  d={`M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`}
                  className={`atlas-v6-route ${fromLive || toLive ? "is-live" : ""} ${selectedRoute ? "is-selected" : ""}`}
                  stroke={gold ? "url(#routeGold)" : "url(#routeViolet)"}
                />
              );
            })}
          </g>

          <g className="atlas-v6-crescent">
            <circle cx="76" cy="12" r="4.6" />
            <circle className="crescent-cut" cx="78" cy="10.7" r="4.7" />
          </g>

          <g className="atlas-v6-skyline">
            <path d="M78 38 V32 H79 V38 M80 38 V28 H81 V38 M82 38 V23 H83 V38 M84 38 V29 H85 V38 M86 38 V25 H87 V38 M88 38 V30 H89 V38" />
            <path d="M82.5 23 L82.5 20.2 M86.5 25 L86.5 22.4" />
          </g>

          <g className="atlas-v6-birds">
            <path d="M88 18 q1 -1 2 0 q1 -1 2 0" />
            <path d="M91 21 q.8 -.8 1.6 0 q.8 -.8 1.6 0" />
          </g>

          <g className="atlas-v6-music">
            <path d="M4 18 C21 11 32 17 43 16 C54 15 62 21 71 17" />
            <path d="M6 21 C23 14 34 20 45 19 C56 18 64 24 73 20" />
            <path d="M27 91 C42 86 57 91 72 87 C83 84 91 87 99 83" />
            <text x="17" y="17">♪</text><text x="59" y="22">♫</text><text x="39" y="90">♪</text><text x="72" y="88">♫</text>
          </g>

          <g className="atlas-v6-guitar" filter="url(#islandShadow)">
            <path className="guitar-body" d="M69.5 31 C66.4 34.4 67.1 38.2 64.6 41.7 C61.6 46.1 63 50.3 66.5 51.6 C69 52.5 68.1 56.5 65 61.6 C70.1 59.7 73.7 55.4 74.5 51.4 C75.3 47.4 72.6 44.4 74.9 40.1 C77 36 77.4 32.7 75.4 29.6 C73.7 27.2 71.1 28.7 69.5 31 Z" />
            <path className="guitar-inner" d="M69 38 C66.9 41.1 67.2 44.8 69.3 45.8 C71.6 46.8 72.7 44.3 72.1 42 C71.7 40.4 70.5 39.3 69 38 Z" />
            <path className="guitar-inner accent" d="M66.4 50 C67.7 52.3 67.5 55.2 66.2 58.1 C69.2 55.9 70.8 53.4 70.7 51.3 C70.5 49.4 68.3 49 66.4 50 Z" />
            <path className="guitar-neck" d="M72.2 37.5 C75 30.4 77 23.2 79.2 15.8 L81.5 16.5 C79.2 25 77.5 32.4 74.3 40 Z" />
            <path className="guitar-head" d="M79.1 15.7 C79.8 12.5 80 9.6 82 7.6 C83.2 6.4 84.6 7.3 84 8.8 C83.3 10.4 82.3 12.2 82.1 16.8 Z" />
            <path className="guitar-string" d="M73.3 39 C76.1 29.5 78.6 20.4 81.4 9.8" />
            <path className="guitar-string" d="M72.7 39.2 C75.4 29.7 78 20.6 80.8 9.6" />
            <ellipse className="guitar-hole" cx="70.2" cy="44.4" rx="1.6" ry="1.4" />
            <path className="guitar-drip" d="M65 61.2 C65.6 64.3 64.2 67.2 62.5 69.8 C65.4 68.1 67.5 65.5 68.3 62.7 Z" />
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
                aria-label={`${marker.city}, ${marker.state}: ${stats.campaigns} campaigns, ${level.label} demand`}
              >
                <span className="atlas-v6-city-aura" aria-hidden="true" />
                <span className="atlas-v6-city-core" aria-hidden="true" />
                <span className="atlas-v6-city-label" aria-hidden="true">
                  <strong>{marker.city}</strong>
                  <small>{stats.campaigns ? level.label : prominent ? "Open city" : marker.state}</small>
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
