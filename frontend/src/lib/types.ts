export type Location = {
  id: number;
  name: string;
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  is_popular: boolean;
};

export type SubIndex = {
  parameter: string;
  display_name: string;
  sub_index: number;
  concentration_used: number;
  unit: string;
  averaging_period: string;
  coverage_hours: number;
};

export type Aqi = {
  available: boolean;
  value: number | null;
  category: string | null;
  dominant_pollutants: string[];
  calculated_at: string | null;
  methodology: string;
  reason: string | null;
  sub_indices: SubIndex[];
  station_id: number | null;
  station_name: string | null;
};

export type Pollutant = {
  parameter: string;
  display_name: string;
  value: number | null;
  unit: string;
  measured_at: string | null;
  source: string | null;
  status: string;
  average_used: number | null;
  averaging_period: string | null;
};

export type HealthGuidance = {
  category: string;
  summary: string;
  precautions: string[];
  disclaimer: string;
};

export type Weather = {
  temperature_c: number | null;
  humidity_percent: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  precipitation_mm: number | null;
  recorded_at: string | null;
  source: string | null;
  kind: string;
  label: string;
};

export type StationPollutant = {
  parameter: string;
  display_name: string;
  value: number | null;
  unit: string;
  measured_at: string | null;
  source: string | null;
};

export type Station = {
  id: number;
  name: string;
  provider: string;
  latitude: number;
  longitude: number;
  is_monitor: boolean;
  aqi: Aqi;
  pollutants: StationPollutant[];
};

export type HistoryPoint = {
  measured_at: string;
  aqi: number | null;
  category: string | null;
  pollutants: Record<string, number | null>;
};

export type History = {
  location_id: number;
  station_id: number | null;
  station_name: string | null;
  hours: number;
  bucket?: string;
  start?: string | null;
  end?: string | null;
  points: HistoryPoint[];
  note: string;
};

export type ForecastPoint = {
  forecast_for: string;
  parameter: string;
  display_name: string;
  value: number;
  unit: string;
  kind: string;
};

export type Forecast = {
  location_id: number;
  source: string;
  cache: "hit" | "miss" | "stale";
  fetched_at: string | null;
  expires_at: string | null;
  points: ForecastPoint[];
  note: string;
};

export type Overview = {
  location: Location;
  freshness: "recent" | "stale" | "unavailable";
  data_origin: string;
  warnings: string[];
  summary_station: Station | null;
  aqi: Aqi;
  pollutants: Pollutant[];
  health: HealthGuidance | null;
  weather: Weather | null;
  stations: Station[];
  history: History;
  sources: string[];
};
