"use client";

import {
  Activity,
  Check,
  CircleCheck,
  CloudRain,
  Database,
  Droplets,
  HeartPulse,
  Info,
  Layers,
  LoaderCircle,
  MapPin,
  Radio,
  RefreshCw,
  Search,
  Wind,
} from "lucide-react";
import dynamic from "next/dynamic";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import { ComparePanel, ForecastPanel, HistoryPanel } from "@/components/analytics-panels";
import { AqiGauge } from "@/components/aqi-gauge";
import { SiteHeader } from "@/components/site-header";
import { TrendChart } from "@/components/trend-chart";
import { Ambient, AqiBadge, Banner, Formula, SectionHeading, Segmented, Skeleton } from "@/components/ui";
import {
  AQI_MAX,
  categoryForIndex,
  categoryStyle,
  compass,
  formatNumber,
  formatWhen,
  FRESHNESS_LABEL,
  POLLUTANTS,
} from "@/lib/format";
import type { Location, Overview } from "@/lib/types";

const StationMap = dynamic(() => import("@/components/station-map"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center text-sm text-muted">Loading map…</div>,
});

const STORAGE_KEY = "community-air-location";

const FRESHNESS_COLOR = {
  recent: "var(--aqi-good)",
  stale: "var(--aqi-moderate)",
  unavailable: "var(--aqi-unknown)",
} as const;

type View = "overview" | "explore" | "history";

/** Sets the stagger position for the `.reveal` entrance. */
function order(index: number): CSSProperties {
  return { ["--i" as string]: index };
}

export function AirApp({ view }: { view: View }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<Location[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [searching, setSearching] = useState(false);
  const [locationId, setLocationId] = useState<number | null>(null);
  const [storageReady, setStorageReady] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [pollutant, setPollutant] = useState("pm25");
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved && Number.isFinite(Number(saved))) {
      setLocationId(Number(saved));
    }
    setStorageReady(true);
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    const controller = new AbortController();
    setSearching(true);
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/v1/locations?q=${encodeURIComponent(query)}`, {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error("search failed");
        const body = (await response.json()) as { results: Location[] };
        setResults(body.results);
        setActiveIndex(0);
        setLocationId((current) => current ?? body.results[0]?.id ?? null);
        setSearching(false);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setSearching(false);
          setError("Location search failed. Is the API running?");
        }
      }
    }, 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, storageReady]);

  useEffect(() => {
    if (!locationId) return;
    window.localStorage.setItem(STORAGE_KEY, String(locationId));
    const controller = new AbortController();
    setLoading(true);
    setOverview(null);
    setError("");
    fetch(`/api/v1/locations/${locationId}/overview`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("overview failed");
        return (await response.json()) as Overview;
      })
      .then((body) => {
        setOverview(body);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setLoading(false);
        setError("The dashboard could not load this location. Check that the API is running on port 8000.");
      });
    return () => controller.abort();
  }, [locationId]);

  // Close the results when the pointer lands outside the search box.
  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  // "/" jumps to the search box from anywhere on the page.
  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      event.preventDefault();
      inputRef.current?.focus();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const chartRows = useMemo(() => {
    if (!overview) return [];
    return overview.history.points.map((point) => ({
      label: formatWhen(point.measured_at, overview.location.timezone),
      aqi: point.aqi,
      pollutant: point.pollutants[pollutant] ?? null,
    }));
  }, [overview, pollutant]);

  const selectedPollutant = POLLUTANTS.find((item) => item.id === pollutant) ?? POLLUTANTS[0];

  function choose(location: Location) {
    setLocationId(location.id);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      if (results.length === 0) return;
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => (current + step + results.length) % results.length);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  function onSearchSubmit(event: FormEvent) {
    event.preventDefault();
    const location = results[activeIndex];
    if (open && location) choose(location);
  }

  async function onRefresh() {
    if (!locationId) return;
    setRefreshing(true);
    setNotice("");
    try {
      const response = await fetch(`/api/v1/locations/${locationId}/refresh`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) {
        setNotice(body.detail ?? "Refresh failed. Stored readings are still shown.");
      } else {
        setNotice(body.message);
      }
      const overviewResponse = await fetch(`/api/v1/locations/${locationId}/overview`, { cache: "no-store" });
      if (overviewResponse.ok) {
        setOverview((await overviewResponse.json()) as Overview);
      }
    } catch {
      setNotice("Refresh failed. Stored readings are still shown.");
    } finally {
      setRefreshing(false);
    }
  }

  const mood = overview
    ? categoryStyle(overview.aqi.available ? overview.aqi.category : null).solid
    : "rgb(var(--accent))";

  return (
    <div className="aqi-scope min-h-screen" style={{ ["--aqi-current" as string]: mood }}>
      <Ambient />
      <SiteHeader />
      <main id="main" className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-6 sm:pt-8">
        <form onSubmit={onSearchSubmit} className="relative z-30 mb-8 flex flex-col gap-3 sm:flex-row">
          <label htmlFor="location-search" className="sr-only">
            Search city or locality
          </label>
          <div ref={searchRef} className="relative flex-1">
            <div className="card flex items-center gap-3 rounded-2xl px-4 transition duration-200 focus-within:border-accent/60 focus-within:shadow-[0_0_0_4px_rgb(var(--accent)/0.14)]">
              {searching && query ? (
                <LoaderCircle size={18} className="shrink-0 animate-spin text-accent" />
              ) : (
                <Search size={18} className="shrink-0 text-muted" />
              )}
              <input
                ref={inputRef}
                id="location-search"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setOpen(true);
                }}
                onFocus={() => setOpen(true)}
                onKeyDown={onSearchKeyDown}
                placeholder="Search a city: Delhi, Pune, Bengaluru…"
                className="w-full bg-transparent py-3.5 text-base text-ink outline-none placeholder:text-faint"
                autoComplete="off"
                role="combobox"
                aria-expanded={open && results.length > 0}
                aria-controls="location-results"
                aria-autocomplete="list"
                aria-activedescendant={open && results[activeIndex] ? `location-option-${results[activeIndex].id}` : undefined}
              />
              <kbd className="hidden shrink-0 rounded-md border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted sm:block">
                /
              </kbd>
            </div>
            {open && results.length > 0 && (
              <ul
                id="location-results"
                role="listbox"
                aria-label="Matching locations"
                className="absolute inset-x-0 top-full mt-2 max-h-80 animate-pop overflow-auto rounded-2xl border border-line-strong bg-surface-solid p-1.5 shadow-pop"
              >
                {results.map((location, index) => {
                  const active = index === activeIndex;
                  const current = location.id === locationId;
                  return (
                    <li
                      key={location.id}
                      id={`location-option-${location.id}`}
                      role="option"
                      aria-selected={active}
                      onPointerMove={() => setActiveIndex(index)}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => choose(location)}
                      className={`flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 transition-colors duration-100 ${
                        active ? "bg-surface-2" : ""
                      }`}
                    >
                      <MapPin size={16} className={current ? "shrink-0 text-accent" : "shrink-0 text-faint"} />
                      <span className="min-w-0 flex-1 truncate">
                        <span className="font-medium text-ink">{location.name}</span>
                        <span className="ml-2 text-sm text-muted">{location.country}</span>
                      </span>
                      {current && <Check size={15} className="shrink-0 text-accent" strokeWidth={2.6} />}
                      <span className="chip shrink-0 text-muted">
                        {location.is_popular ? "scheduled city" : "on-demand city"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
            {open && query.trim() !== "" && !searching && results.length === 0 && (
              <p
                role="status"
                className="absolute inset-x-0 top-full mt-2 animate-pop rounded-2xl border border-line-strong bg-surface-solid px-4 py-3.5 text-sm text-muted shadow-pop"
              >
                No city matches “{query.trim()}”.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onRefresh}
            className="btn btn-primary rounded-2xl px-5 py-3.5"
            disabled={!locationId || refreshing}
          >
            <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh data"}
          </button>
        </form>

        {(notice || error) && (
          <div className="mb-5 space-y-3">
            {notice && <Banner tone="info">{notice}</Banner>}
            {error && (
              <Banner tone="error" role="alert">
                {error}
              </Banner>
            )}
          </div>
        )}

        {loading && !overview && !error && <DashboardSkeleton />}
        {overview && (
          <DashboardBody
            view={view}
            overview={overview}
            chartRows={chartRows}
            pollutant={pollutant}
            pollutantName={selectedPollutant.name}
            pollutantUnit={selectedPollutant.unit}
            onPollutant={setPollutant}
          />
        )}
      </main>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5" role="status" aria-live="polite">
      <span className="sr-only">Loading air quality…</span>
      <div className="space-y-3">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-16 w-72 max-w-full" />
        <Skeleton className="h-3 w-80 max-w-full" />
      </div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-12">
        <Skeleton className="h-80 rounded-3xl xl:col-span-5" />
        <Skeleton className="h-80 rounded-3xl xl:col-span-4" />
        <Skeleton className="h-80 rounded-3xl md:col-span-2 xl:col-span-3" />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {POLLUTANTS.map((item) => (
          <Skeleton key={item.id} className="h-36 rounded-3xl" />
        ))}
      </div>
    </div>
  );
}

function DashboardBody({
  view,
  overview,
  chartRows,
  pollutant,
  pollutantName,
  pollutantUnit,
  onPollutant,
}: {
  view: View;
  overview: Overview;
  chartRows: { label: string; aqi: number | null; pollutant: number | null }[];
  pollutant: string;
  pollutantName: string;
  pollutantUnit: string;
  onPollutant: (value: string) => void;
}) {
  const style = categoryStyle(overview.aqi.available ? overview.aqi.category : null);
  const [stationFilter, setStationFilter] = useState("all");
  const [activeStation, setActiveStation] = useState<number | null>(null);
  const visibleStations = overview.stations.filter((station) => {
    if (stationFilter === "all") return true;
    if (stationFilter === "aqi") return station.aqi.available;
    return station.pollutants.some((item) => item.parameter === stationFilter && item.value !== null);
  });
  const updated = overview.aqi.calculated_at ?? overview.pollutants.find((item) => item.measured_at)?.measured_at;
  const { location } = overview;
  const coordinates = `${Math.abs(location.latitude).toFixed(2)}°${location.latitude >= 0 ? "N" : "S"} ${Math.abs(
    location.longitude,
  ).toFixed(2)}°${location.longitude >= 0 ? "E" : "W"}`;

  return (
    <div className="space-y-5">
      {overview.warnings.map((warning) => (
        <Banner key={warning} tone="warn">
          {warning}
        </Banner>
      ))}

      <div className="reveal flex flex-wrap items-end justify-between gap-x-6 gap-y-4 pb-1 pt-2">
        <div className="min-w-0">
          <p className="eyebrow flex items-center gap-2">
            <MapPin size={13} style={{ color: style.text }} />
            {location.country} · {coordinates}
          </p>
          <h1 className="mt-2 font-display text-6xl leading-[0.95] tracking-[-0.01em] text-ink sm:text-7xl">
            {location.name}
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            {overview.summary_station ? `Readings from ${overview.summary_station.name}` : "No station selected"}
            {updated ? ` · Last measurement ${formatWhen(updated, location.timezone)}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="chip py-1.5">
            <span className="relative flex h-2 w-2">
              {overview.freshness === "recent" && (
                <span
                  className="absolute inset-0 animate-ping rounded-full"
                  style={{ background: FRESHNESS_COLOR.recent }}
                />
              )}
              <span
                className="relative h-2 w-2 rounded-full"
                style={{ background: FRESHNESS_COLOR[overview.freshness] }}
              />
            </span>
            <span className="text-muted">Data status:</span>
            <span className="font-semibold">{FRESHNESS_LABEL[overview.freshness]}</span>
          </p>
          <p className="chip py-1.5 font-mono text-[11px] uppercase tracking-wider text-muted">
            <Database size={12} />
            {overview.data_origin}
          </p>
        </div>
      </div>

      {(view === "overview" || view === "history") && (
        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-12">
          <article className="card aqi-glow reveal p-5 sm:p-6 xl:col-span-5" style={order(1)}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="eyebrow">Current AQI</h2>
                <p className="mt-1.5 text-xs text-muted">Indian AQI · {overview.aqi.methodology}</p>
              </div>
              {overview.aqi.available && overview.aqi.dominant_pollutants.length > 0 && (
                <p className="chip" style={{ borderColor: `color-mix(in srgb, ${style.solid} 40%, transparent)` }}>
                  <span className="text-muted">Dominant pollutant:</span>
                  <span className="font-semibold" style={{ color: style.text }}>
                    {overview.aqi.dominant_pollutants.map((name, index) => (
                      <span key={name}>
                        {index > 0 && ", "}
                        <Formula name={name} />
                      </span>
                    ))}
                  </span>
                </p>
              )}
            </div>
            <div className="mt-3">
              <AqiGauge value={overview.aqi.value} category={overview.aqi.category} available={overview.aqi.available} />
            </div>
            {!overview.aqi.available && (
              <p className="mx-auto mt-2 max-w-sm text-center text-sm leading-6 text-muted">{overview.aqi.reason}</p>
            )}
          </article>

          <article
            className={`card reveal p-5 sm:p-6 ${view === "overview" ? "xl:col-span-4" : "xl:col-span-7"}`}
            style={order(2)}
          >
            <h2 className="eyebrow flex items-center gap-2">
              <HeartPulse size={14} style={{ color: style.text }} />
              Health guidance
            </h2>
            {overview.health ? (
              <>
                <p className="mt-4 font-display text-[1.75rem] leading-[1.14] text-ink">{overview.health.summary}</p>
                <ul className="mt-5 space-y-2.5">
                  {overview.health.precautions.map((item) => (
                    <li key={item} className="flex gap-3 text-sm leading-6 text-ink">
                      <CircleCheck size={17} className="mt-[3px] shrink-0" style={{ color: style.text }} />
                      {item}
                    </li>
                  ))}
                </ul>
                <p className="mt-5 flex gap-2 border-t border-line pt-4 text-xs leading-5 text-muted">
                  <Info size={14} className="mt-0.5 shrink-0" />
                  {overview.health.disclaimer}
                </p>
              </>
            ) : (
              <p className="mt-4 text-sm leading-6 text-muted">
                Health guidance is hidden because a valid CPCB AQI could not be calculated.
              </p>
            )}
          </article>

          {view === "overview" && <WeatherCard overview={overview} />}
        </section>
      )}

      {view === "overview" && (
        <section aria-label="Pollutants" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {overview.pollutants.map((item, index) => {
            const sub = overview.aqi.sub_indices.find((entry) => entry.parameter === item.parameter);
            const subStyle = categoryStyle(categoryForIndex(sub?.sub_index));
            const dominant = overview.aqi.available && overview.aqi.dominant_pollutants.includes(item.display_name);
            const missing = item.value === null;
            return (
              <article
                key={item.parameter}
                className={`card reveal flex flex-col p-4 transition duration-300 hover:-translate-y-0.5 hover:border-line-strong ${
                  missing ? "border-dashed" : ""
                }`}
                style={order(index + 3)}
              >
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-sm font-medium text-muted">
                    <Formula name={item.display_name} />
                  </h2>
                  {dominant && (
                    <span
                      className="rounded-full px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-wider"
                      style={{ background: style.soft, color: style.text }}
                    >
                      Dominant
                    </span>
                  )}
                </div>
                <p
                  className={`mt-3 font-semibold leading-none tracking-tight tabular-nums ${
                    missing ? "text-lg text-faint" : "text-[1.8rem] text-ink"
                  }`}
                >
                  {missing ? "Unavailable" : formatNumber(item.value, item.parameter === "co" ? 2 : 1)}
                </p>
                <p className="mt-1.5 text-xs text-muted">{missing ? "No reading stored" : item.unit}</p>
                {sub && (
                  <div className="mt-3">
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="bar-grow h-full rounded-full"
                        style={{
                          width: `${Math.max(3, Math.min(100, (sub.sub_index / AQI_MAX) * 100))}%`,
                          background: subStyle.solid,
                          ...order(index + 3),
                        }}
                      />
                    </div>
                    <p className="mt-1.5 text-[11px] text-muted">
                      Sub-index{" "}
                      <span className="font-semibold tabular-nums" style={{ color: subStyle.text }}>
                        {sub.sub_index}
                      </span>
                    </p>
                  </div>
                )}
                <div className="mt-auto pt-3">
                  {item.average_used !== null && (
                    <p className="text-[11px] leading-4 text-muted">
                      {item.averaging_period} average used for AQI:{" "}
                      {formatNumber(item.average_used, item.parameter === "co" ? 1 : 0)} {item.unit}
                    </p>
                  )}
                  {!missing && (
                    <p className="mt-1.5 text-[11px] leading-4 text-faint">
                      {item.source ?? "stored"} · {formatWhen(item.measured_at, location.timezone)}
                    </p>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      )}

      {view === "overview" && (
        <section className="grid gap-5 xl:grid-cols-12">
          <article className="card reveal p-5 sm:p-6 xl:col-span-8" style={order(4)}>
            <SectionHeading
              icon={<Activity size={17} />}
              title="Recent trend"
              hint={`The last ${overview.history.hours} hours at this station.`}
            >
              <Segmented label="Pollutant" value={pollutant} onChange={onPollutant} options={POLLUTANTS} formula />
            </SectionHeading>
            <div className="mt-5">
              <TrendChart rows={chartRows} pollutantName={pollutantName} unit={pollutantUnit} />
            </div>
            <p className="mt-3 text-xs leading-5 text-muted">
              {overview.history.station_name ? `Station: ${overview.history.station_name}. ` : ""}
              {overview.history.note} AQI is unitless. {pollutantName} is shown in {pollutantUnit}. Hourly observations.
            </p>
          </article>
          <SubIndexCard overview={overview} />
        </section>
      )}

      {view === "overview" && <ForecastPanel locationId={location.id} timeZone={location.timezone} />}

      {view === "history" && (
        <>
          <HistoryPanel locationId={location.id} timeZone={location.timezone} />
          <ForecastPanel locationId={location.id} timeZone={location.timezone} />
          <ComparePanel locationId={location.id} />
        </>
      )}

      {(view === "overview" || view === "explore") && (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(18rem,0.8fr)]">
          <article className="card reveal overflow-hidden" style={order(1)}>
            <div className="p-5 sm:px-6">
              <SectionHeading
                icon={<Radio size={17} />}
                title="Monitoring stations"
                hint="Each pin is a physical monitor, labelled with its AQI."
              >
                <label className="flex items-center gap-2 text-xs text-muted">
                  Filter
                  <select
                    value={stationFilter}
                    onChange={(event) => {
                      setStationFilter(event.target.value);
                      setActiveStation(null);
                    }}
                    className="field py-1.5"
                  >
                    <option value="all">All stations</option>
                    <option value="aqi">AQI available</option>
                    <option value="pm25">Has PM2.5</option>
                    <option value="pm10">Has PM10</option>
                    <option value="no2">Has NO2</option>
                    <option value="so2">Has SO2</option>
                    <option value="co">Has CO</option>
                    <option value="o3">Has O3</option>
                  </select>
                </label>
              </SectionHeading>
            </div>
            <div className={`isolate border-y border-line ${view === "explore" ? "h-[34rem]" : "h-[24rem]"}`}>
              <StationMap
                key={`${location.id}-${stationFilter}`}
                stations={visibleStations}
                center={[location.latitude, location.longitude]}
                activeId={activeStation}
                onSelect={setActiveStation}
              />
            </div>
            <p className="px-5 py-3.5 text-xs leading-5 text-muted sm:px-6">
              Markers are physical monitoring stations. This map is not an interpolated pollution surface.
            </p>
          </article>

          <article className="card reveal flex flex-col p-5 sm:p-6" style={order(2)}>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold tracking-tight text-ink">Stations</h2>
              <span className="chip tabular-nums text-muted">
                {visibleStations.length} of {overview.stations.length}
              </span>
            </div>
            <ul
              className={`-mr-2 mt-4 space-y-2.5 overflow-y-auto pr-2 ${
                view === "explore" ? "lg:max-h-[36rem]" : "lg:max-h-[26rem]"
              }`}
            >
              {visibleStations.length === 0 && (
                <li className="rounded-2xl border border-dashed border-line p-4 text-sm text-muted">
                  No stations match this filter.
                </li>
              )}
              {visibleStations.map((station) => {
                const active = station.id === activeStation;
                return (
                  <li key={station.id}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => setActiveStation(station.id)}
                      title="Show this station on the map"
                      className={`w-full rounded-2xl border p-3.5 text-left transition duration-200 ${
                        active ? "border-accent/60 bg-accent/10" : "border-line bg-surface-2 hover:border-line-strong"
                      }`}
                    >
                      <p className="text-sm font-medium leading-5 text-ink">{station.name}</p>
                      <p className="mt-1 font-mono text-[11px] text-muted">
                        {station.latitude.toFixed(4)}, {station.longitude.toFixed(4)} · {station.provider}
                      </p>
                      <p className="mt-2.5">
                        <AqiBadge
                          value={station.aqi.available ? station.aqi.value : null}
                          category={station.aqi.category}
                          size="sm"
                        />
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          </article>
        </section>
      )}

      <footer className="card px-5 py-4 sm:px-6">
        <p className="eyebrow">Sources</p>
        <ul className="mt-2.5 space-y-1 text-xs leading-5 text-muted">
          {overview.sources.map((source) => (
            <li key={source}>{source}</li>
          ))}
        </ul>
      </footer>
    </div>
  );
}

function SubIndexCard({ overview }: { overview: Overview }) {
  const subs = [...overview.aqi.sub_indices].sort((left, right) => right.sub_index - left.sub_index);
  return (
    <article className="card reveal p-5 sm:p-6 xl:col-span-4" style={order(5)}>
      <SectionHeading
        icon={<Layers size={17} />}
        title="What sets the AQI"
        hint="Each pollutant gets a sub-index. The overall AQI is the highest valid one."
      />
      {subs.length === 0 ? (
        <p className="mt-5 text-sm leading-6 text-muted">No sub-index could be calculated from the stored readings.</p>
      ) : (
        <ol className="mt-5 space-y-4">
          {subs.map((sub, index) => {
            const subStyle = categoryStyle(categoryForIndex(sub.sub_index));
            const leading = overview.aqi.available && index === 0;
            return (
              <li key={sub.parameter}>
                <div className="flex items-baseline justify-between gap-3">
                  <p className="flex items-center gap-2 text-sm font-medium text-ink">
                    <span>
                      <Formula name={sub.display_name} />
                    </span>
                    {leading && (
                      <span
                        className="rounded-full px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-wider"
                        style={{ background: subStyle.soft, color: subStyle.text }}
                      >
                        Sets the AQI
                      </span>
                    )}
                  </p>
                  <p className="text-sm font-semibold tabular-nums" style={{ color: subStyle.text }}>
                    {sub.sub_index}
                  </p>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className="bar-grow h-full rounded-full"
                    style={{
                      width: `${Math.max(2, Math.min(100, (sub.sub_index / AQI_MAX) * 100))}%`,
                      background: subStyle.solid,
                      ...order(index + 4),
                    }}
                  />
                </div>
                <p className="mt-1.5 text-[11px] leading-4 text-muted">
                  {formatNumber(sub.concentration_used, sub.parameter === "co" ? 1 : 0)} {sub.unit} ·{" "}
                  {sub.averaging_period} average · {sub.coverage_hours} h of data
                </p>
              </li>
            );
          })}
        </ol>
      )}
      {!overview.aqi.available && overview.aqi.reason && (
        <p className="mt-5 border-t border-line pt-4 text-xs leading-5 text-muted">{overview.aqi.reason}</p>
      )}
    </article>
  );
}

function WeatherCard({ overview }: { overview: Overview }) {
  const weather = overview.weather;
  const stats = weather
    ? [
        {
          icon: <Droplets size={15} />,
          label: "Humidity",
          value: weather.humidity_percent === null ? "Unavailable" : `${formatNumber(weather.humidity_percent, 0)}%`,
        },
        {
          icon: <Wind size={15} />,
          label: "Wind",
          value:
            weather.wind_speed_kmh === null
              ? "Unavailable"
              : `${formatNumber(weather.wind_speed_kmh, 0)} km/h ${compass(weather.wind_direction_deg)}`,
        },
        {
          icon: <CloudRain size={15} />,
          label: "Precipitation",
          value: weather.precipitation_mm === null ? "Unavailable" : `${formatNumber(weather.precipitation_mm, 1)} mm`,
        },
      ]
    : [];

  return (
    <article className="card reveal flex flex-col p-5 sm:p-6 md:col-span-2 xl:col-span-3" style={order(3)}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="eyebrow">Weather</h2>
        {weather && <span className="chip font-mono text-[10px] uppercase tracking-wider text-muted">{weather.kind}</span>}
      </div>
      {weather ? (
        <>
          <div className="mt-4 md:flex md:items-end md:gap-10 xl:block">
            <div>
              {weather.temperature_c === null ? (
                <p className="text-lg font-semibold text-faint">Unavailable</p>
              ) : (
                <p className="flex items-start text-ink">
                  <span className="text-6xl font-light leading-none tracking-[-0.05em] tabular-nums">
                    {formatNumber(weather.temperature_c, 1)}
                  </span>
                  <span className="ml-1 mt-1 text-xl text-muted">°C</span>
                </p>
              )}
              <p className="mt-2 text-xs text-muted">Temperature</p>
            </div>
            <dl className="mt-5 grid flex-1 gap-2 sm:grid-cols-3 md:mt-0 xl:mt-5 xl:grid-cols-1">
              {stats.map((stat) => (
                <div
                  key={stat.label}
                  className="flex items-center justify-between gap-3 rounded-xl border border-line bg-surface-2 px-3 py-2.5 text-sm"
                >
                  <dt className="flex items-center gap-2 text-muted">
                    <span className="text-accent">{stat.icon}</span>
                    {stat.label}
                  </dt>
                  <dd className="font-medium tabular-nums text-ink">{stat.value}</dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="mt-auto pt-4 text-xs leading-5 text-muted">{weather.label}</p>
        </>
      ) : (
        <p className="mt-4 text-sm text-muted">Weather is unavailable.</p>
      )}
    </article>
  );
}
