/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Visualizes demand across major US cities without adding a heavyweight mapping dependency.
 */

import { MapPin, Radio, Sparkles } from "lucide-react";
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

export function DiscoveryMap({ campaigns, selectedCity, onSelectCity }: Props) {
  const demand = new Map<string, { campaigns: number; supporters: number }>();
  for (const campaign of campaigns) {
    const city = CITY_ALIASES[campaign.city.trim().toLowerCase()] ?? campaign.city.trim();
    const current = demand.get(city) ?? { campaigns: 0, supporters: 0 };
    current.campaigns += 1;
    current.supporters += campaign.preference_summary?.expected_attendance ?? campaign.active_supporter_count ?? 0;
    demand.set(city, current);
  }

  return (
    <section className="demand-map-card" aria-label="United States live demand map">
      <div className="map-card-heading">
        <div>
          <span className="map-kicker"><Radio size={14} /> Live demand network</span>
          <h2>Choose a city from the map</h2>
          <p>See proposed gigs, active demand, and confirmed shows city by city.</p>
        </div>
        <div className="map-legend" aria-label="Map legend">
          <span><i className="legend-dot demand" /> Demand</span>
          <span><i className="legend-dot active" /> Active</span>
          <span><i className="legend-dot confirmed" /> Confirmed</span>
        </div>
      </div>

      <div className="map-perspective-shell">
        <div className="map-grid-plane" aria-hidden="true" />
        <div className="map-coast-shape" aria-hidden="true" />
        {MAJOR_US_CITIES.map((marker) => {
          const stats = demand.get(marker.city) ?? { campaigns: 0, supporters: 0 };
          const active = selectedCity.toLowerCase() === marker.city.toLowerCase();
          const intensity = Math.min(4, Math.max(1, Math.ceil((stats.supporters || stats.campaigns * 25) / 250)));
          return (
            <button
              key={`${marker.city}-${marker.state}`}
              type="button"
              className={`map-city-marker intensity-${intensity} ${active ? "is-selected" : ""}`}
              style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
              onClick={() => onSelectCity(marker.city, marker.state)}
              aria-label={`${marker.city}, ${marker.state}: ${stats.campaigns} campaigns`}
            >
              <span className="marker-pulse" />
              <MapPin size={18} aria-hidden="true" />
              <span className="marker-label">
                <strong>{marker.city}</strong>
                <small>{stats.campaigns ? `${stats.campaigns} gigs · ${stats.supporters.toLocaleString()} demand` : "Open city"}</small>
              </span>
            </button>
          );
        })}
        <div className="map-network-badge">
          <Sparkles size={16} />
          <span>Demand becomes the tour map</span>
        </div>
      </div>
    </section>
  );
}
