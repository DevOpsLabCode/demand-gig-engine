/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Uses the approved Open Concert atlas artwork as the visual map while keeping real accessible city interactions.
 */

import type { Campaign } from "../types";

export interface CityMarker {
  city: string;
  state: string;
  x: number;
  y: number;
}

export const MAJOR_US_CITIES: CityMarker[] = [
  { city: "Seattle", state: "WA", x: 12, y: 17 },
  { city: "Portland", state: "OR", x: 11, y: 25 },
  { city: "San Francisco", state: "CA", x: 9.5, y: 48 },
  { city: "Los Angeles", state: "CA", x: 14, y: 66 },
  { city: "San Diego", state: "CA", x: 16, y: 74 },
  { city: "Las Vegas", state: "NV", x: 23, y: 60 },
  { city: "Phoenix", state: "AZ", x: 29, y: 69 },
  { city: "Salt Lake City", state: "UT", x: 31, y: 43 },
  { city: "Denver", state: "CO", x: 36.5, y: 47 },
  { city: "Dallas", state: "TX", x: 49, y: 72 },
  { city: "Austin", state: "TX", x: 46, y: 69 },
  { city: "Houston", state: "TX", x: 54, y: 77 },
  { city: "Minneapolis", state: "MN", x: 59, y: 31 },
  { city: "Chicago", state: "IL", x: 66, y: 43 },
  { city: "Nashville", state: "TN", x: 65, y: 60 },
  { city: "New Orleans", state: "LA", x: 59, y: 79 },
  { city: "Atlanta", state: "GA", x: 73, y: 64 },
  { city: "Miami", state: "FL", x: 85, y: 82 },
  { city: "Washington", state: "DC", x: 82, y: 52 },
  { city: "Philadelphia", state: "PA", x: 85, y: 48 },
  { city: "New York", state: "NY", x: 86.5, y: 49 },
  { city: "Boston", state: "MA", x: 92, y: 42 },
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

function levelFor(campaigns: number, supporters: number, progress: number) {
  const score = supporters + campaigns * 80 + progress * 4;
  if (score >= 1000) return "very-high";
  if (score >= 420) return "high";
  if (score >= 120) return "rising";
  return campaigns ? "emerging" : "open";
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

  return (
    <section className="demand-map-card atlas-v5" aria-label="United States live demand map">
      <div className="atlas-v5-shell">
        <div className="atlas-v5-approved-art" aria-hidden="true" />

        <div className="atlas-v5-hotspots" aria-label="Choose a city on the map">
          {MAJOR_US_CITIES.map((marker) => {
            const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0, progress: 0 };
            const active = selectedCity.trim().toLowerCase() === marker.city.toLowerCase();
            const level = levelFor(stats.campaigns, stats.supporters, stats.progress);

            return (
              <button
                key={`${marker.city}-${marker.state}`}
                type="button"
                className={`atlas-v5-hotspot is-${level} ${active ? "is-selected" : ""} ${stats.campaigns ? "has-demand" : ""}`}
                style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
                onClick={() => onSelectCity(marker.city, marker.state)}
                aria-label={`${marker.city}, ${marker.state}${stats.campaigns ? `, ${stats.campaigns} active demand ${stats.campaigns === 1 ? "campaign" : "campaigns"}` : ", open city"}`}
                title={`${marker.city}, ${marker.state}`}
              >
                <span className="atlas-v5-hit-ring" aria-hidden="true" />
                <span className="atlas-v5-tooltip" aria-hidden="true">
                  <strong>{marker.city}</strong>
                  <small>{stats.campaigns ? `${stats.campaigns} ${stats.campaigns === 1 ? "gig" : "gigs"} · ${Math.round(stats.progress)}%` : "Open city"}</small>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
