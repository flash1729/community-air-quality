export type CategoryStyle = {
  /** Fill colour for gauges, bars and map pins. Same in both themes. */
  solid: string;
  /** Text colour that stays readable on a card in the current theme. */
  text: string;
  /** Text colour to use on top of `solid`. */
  on: string;
  /** Faint tint of `solid` for badge backgrounds. */
  soft: string;
};

function style(token: string, on = "var(--aqi-on)"): CategoryStyle {
  return {
    solid: `var(--aqi-${token})`,
    text: `var(--aqi-${token}-text)`,
    on,
    soft: `color-mix(in srgb, var(--aqi-${token}) 16%, transparent)`,
  };
}

const UNKNOWN = style("unknown");

export const CATEGORIES: Record<string, CategoryStyle> = {
  Good: style("good"),
  Satisfactory: style("satisfactory"),
  Moderate: style("moderate"),
  Poor: style("poor"),
  "Very Poor": style("very-poor"),
  Severe: style("severe", "var(--aqi-severe-on)"),
};

/** CPCB National AQI bands, matching the backend's category table. */
export const AQI_SCALE = [
  { category: "Good", min: 0, max: 50 },
  { category: "Satisfactory", min: 51, max: 100 },
  { category: "Moderate", min: 101, max: 200 },
  { category: "Poor", min: 201, max: 300 },
  { category: "Very Poor", min: 301, max: 400 },
  { category: "Severe", min: 401, max: 500 },
] as const;

export const AQI_MAX = 500;

export function categoryStyle(category: string | null | undefined): CategoryStyle {
  if (!category || !CATEGORIES[category]) return UNKNOWN;
  return CATEGORIES[category];
}

/** Band for an index value. Used to colour sub-indices, which arrive without a category. */
export function categoryForIndex(value: number | null | undefined): string | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const bounded = Math.max(0, Math.min(AQI_MAX, Math.round(value)));
  return AQI_SCALE.find((band) => bounded >= band.min && bounded <= band.max)?.category ?? "Severe";
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Unavailable";
  }
  return value.toFixed(digits);
}

export function formatWhen(value: string | null | undefined, timeZone: string): string {
  if (!value) return "Unknown time";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone,
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function compass(degrees: number | null): string {
  if (degrees === null || Number.isNaN(degrees)) return "";
  const names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return names[Math.round((((degrees % 360) + 360) % 360) / 45) % 8];
}

export const FRESHNESS_LABEL = {
  recent: "Recent",
  stale: "Stale",
  unavailable: "Unavailable",
} as const;

export const POLLUTANTS = [
  { id: "pm25", name: "PM2.5", unit: "µg/m³" },
  { id: "pm10", name: "PM10", unit: "µg/m³" },
  { id: "no2", name: "NO2", unit: "µg/m³" },
  { id: "so2", name: "SO2", unit: "µg/m³" },
  { id: "co", name: "CO", unit: "mg/m³" },
  { id: "o3", name: "O3", unit: "µg/m³" },
];
