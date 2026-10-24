"use client";

import { CalendarClock, Check, Database, Download, GitCompareArrows, LoaderCircle, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { CITY_COLORS, CompareCharts, type ComparedSeries } from "@/components/compare-chart";
import { TrendChart } from "@/components/trend-chart";
import { AqiBadge, Banner, Formula, SectionHeading, Segmented } from "@/components/ui";
import { formatWhen, POLLUTANTS } from "@/lib/format";
import type { Forecast, History, HistoryPoint, Location } from "@/lib/types";

const BUCKETS = [
  { id: "hour", name: "Hourly" },
  { id: "day", name: "Daily mean" },
];

const RESULT_COLUMNS: Record<number, string> = {
  2: "xl:grid-cols-2",
  3: "xl:grid-cols-3",
  4: "xl:grid-cols-4",
};

function utcDate(offsetDays: number) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

export function HistoryPanel({ locationId, timeZone }: { locationId: number; timeZone: string }) {
  const [start, setStart] = useState(() => utcDate(-1));
  const [end, setEnd] = useState(() => utcDate(0));
  const [bucket, setBucket] = useState("hour");
  const [pollutant, setPollutant] = useState("pm25");
  const [history, setHistory] = useState<History | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ start, end, bucket });
    fetch(`/api/v1/locations/${locationId}/history?${params}`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail ?? "History could not be loaded.");
        }
        return (await response.json()) as History;
      })
      .then((body) => {
        setHistory(body);
        setError("");
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setError(err.message);
      });
    return () => controller.abort();
  }, [locationId, start, end, bucket]);

  const selected = POLLUTANTS.find((item) => item.id === pollutant) ?? POLLUTANTS[0];
  const rows = useMemo(() => {
    if (!history) return [];
    return history.points.map((point) => ({
      label: formatWhen(point.measured_at, timeZone),
      aqi: point.aqi,
      pollutant: point.pollutants[pollutant] ?? null,
    }));
  }, [history, pollutant, timeZone]);

  function onDates(event: FormEvent) {
    event.preventDefault();
  }

  return (
    <article className="card p-5 sm:p-6">
      <SectionHeading
        icon={<Database size={17} />}
        title="Stored history"
        hint="Read from the database. This request does not call OpenAQ."
      >
        <a
          className="btn btn-ghost px-3.5 py-2"
          href={`/api/v1/locations/${locationId}/export?start=${start}&end=${end}`}
          download
        >
          <Download size={15} />
          Download CSV
        </a>
      </SectionHeading>

      <form onSubmit={onDates} className="mt-5 flex flex-wrap items-end gap-x-4 gap-y-3">
        <label className="eyebrow block">
          Start (UTC)
          <input
            type="date"
            value={start}
            onChange={(event) => setStart(event.target.value)}
            className="field mt-1.5 block font-sans normal-case tracking-normal"
          />
        </label>
        <label className="eyebrow block">
          End (UTC)
          <input
            type="date"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
            className="field mt-1.5 block font-sans normal-case tracking-normal"
          />
        </label>
        <div>
          <p className="eyebrow mb-1.5">Summary</p>
          <Segmented label="Summary" value={bucket} onChange={setBucket} options={BUCKETS} />
        </div>
        <div className="min-w-0 max-w-full">
          <p className="eyebrow mb-1.5">Pollutant</p>
          <Segmented label="Pollutant" value={pollutant} onChange={setPollutant} options={POLLUTANTS} formula />
        </div>
      </form>

      <div className="mt-5">
        {error && (
          <div className="mb-4">
            <Banner tone="error" role="alert">
              {error}
            </Banner>
          </div>
        )}
        <TrendChart rows={rows} pollutantName={selected.name} unit={selected.unit} loading={!history && !error} />
      </div>
      <p className="mt-3 text-xs leading-5 text-muted">
        {history?.station_name ? `Station: ${history.station_name}. ` : ""}
        {history?.note} Dates are UTC, matching the stored timestamps.
      </p>
    </article>
  );
}

type CompareRow = {
  id: number;
  name: string;
  origin: string;
  freshness: string;
  station: string | null;
  aqiValue: number | null;
  category: string | null;
  reason: string | null;
  pollutants: { parameter: string; display_name: string; value: number | null; unit: string }[];
};

export function ComparePanel({ locationId }: { locationId: number }) {
  const [options, setOptions] = useState<Location[]>([]);
  const [selected, setSelected] = useState<number[]>([locationId]);
  const [error, setError] = useState("");
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [series, setSeries] = useState<ComparedSeries[]>([]);
  const [note, setNote] = useState("");
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    fetch("/api/v1/locations?limit=50", { cache: "no-store" })
      .then((response) => response.json())
      .then((body: { results: Location[] }) => setOptions(body.results))
      .catch(() => setError("Saved cities could not be loaded."));
  }, []);

  useEffect(() => {
    setSelected((current) => (current.includes(locationId) ? current : [locationId, ...current].slice(0, 4)));
  }, [locationId]);

  function toggle(id: number) {
    setSelected((current) => {
      if (current.includes(id)) return current.filter((item) => item !== id);
      if (current.length >= 4) return current;
      return [...current, id];
    });
  }

  async function onCompare(event: FormEvent) {
    event.preventDefault();
    if (selected.length < 2) {
      setError("Choose at least two cities.");
      setRows([]);
      setSeries([]);
      return;
    }
    setError("");
    setComparing(true);
    try {
      const response = await fetch(`/api/v1/compare?ids=${selected.join(",")}`, { cache: "no-store" });
      const body = await response.json();
      if (!response.ok) {
        setError(body.detail ?? "Comparison failed.");
        setRows([]);
        setSeries([]);
        return;
      }
      const locations = body.locations as {
        location: Location;
        data_origin: string;
        freshness: string;
        summary_station: string | null;
        aqi: { available: boolean; value: number | null; category: string | null; reason: string | null };
        pollutants: { parameter: string; display_name: string; value: number | null; unit: string }[];
      }[];
      const histories = await Promise.all(
        locations.map(async (item) => {
          const historyResponse = await fetch(`/api/v1/locations/${item.location.id}/history?hours=48`, {
            cache: "no-store",
          });
          if (!historyResponse.ok) return [] as HistoryPoint[];
          const history = (await historyResponse.json()) as History;
          return history.points;
        }),
      );
      setNote(body.note);
      setSeries(
        locations.map((item, index) => ({
          id: item.location.id,
          name: item.location.name,
          aqiValue: item.aqi.available ? item.aqi.value : null,
          pollutantValues: Object.fromEntries(item.pollutants.map((pollutant) => [pollutant.parameter, pollutant.value])),
          points: histories[index] ?? [],
        })),
      );
      setRows(
        locations.map((item) => ({
          id: item.location.id,
          name: item.location.name,
          origin: item.data_origin,
          freshness: item.freshness,
          station: item.summary_station,
          aqiValue: item.aqi.available ? item.aqi.value : null,
          category: item.aqi.available ? item.aqi.category : null,
          reason: item.aqi.available ? null : item.aqi.reason,
          pollutants: item.pollutants,
        })),
      );
    } catch {
      setError("Comparison failed. If this city has not been opened before, the station fetch may still be running.");
      setRows([]);
      setSeries([]);
    } finally {
      setComparing(false);
    }
  }

  return (
    <article className="card p-5 sm:p-6">
      <SectionHeading
        icon={<GitCompareArrows size={17} />}
        title="Compare stored cities"
        hint="Up to four cities. A city you have not opened yet is loaded from OpenAQ when you compare."
      >
        <span className="chip tabular-nums">{selected.length} of 4 selected</span>
      </SectionHeading>

      <form onSubmit={onCompare} className="mt-5 space-y-4">
        <ul className="flex flex-wrap gap-2">
          {options.map((location) => {
            const active = selected.includes(location.id);
            const full = !active && selected.length >= 4;
            return (
              <li key={location.id}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggle(location.id)}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition duration-200 ${
                    active
                      ? "border-accent/50 bg-accent/10 font-semibold text-accent"
                      : `border-line bg-surface-2 text-ink hover:border-line-strong ${full ? "opacity-50" : ""}`
                  }`}
                >
                  {active && <Check size={14} strokeWidth={3} />}
                  {location.name}
                  <span className={`text-xs font-normal ${active ? "text-accent/80" : "text-muted"}`}>
                    {location.country} · {location.is_popular ? "scheduled" : "on demand"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <button type="submit" disabled={comparing} className="btn btn-primary">
          {comparing ? <LoaderCircle size={16} className="animate-spin" /> : <GitCompareArrows size={16} />}
          {comparing ? "Loading stations…" : "Compare"}
        </button>
      </form>

      {comparing && (
        <p className="mt-4 text-sm text-muted">
          Cities that have not been opened yet are being loaded from OpenAQ. This can take up to a minute.
        </p>
      )}
      {error && (
        <div className="mt-4">
          <Banner tone="error" role="alert">
            {error}
          </Banner>
        </div>
      )}

      {rows.length > 0 && (
        <div className="mt-6">
          <ul className={`grid gap-3 sm:grid-cols-2 ${RESULT_COLUMNS[rows.length] ?? "xl:grid-cols-4"}`}>
            {rows.map((row, index) => {
              const color = CITY_COLORS[index % CITY_COLORS.length];
              return (
                <li
                  key={row.id}
                  className="reveal overflow-hidden rounded-2xl border border-line bg-surface-2"
                  style={{ ["--i" as string]: index }}
                >
                  <div className="h-1" style={{ background: color }} />
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-base font-semibold text-ink">{row.name}</p>
                        <p className="mt-0.5 text-xs leading-5 text-muted">
                          {row.station ?? "No station"} · {row.freshness}
                        </p>
                      </div>
                      <span className="chip shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted">
                        {row.origin}
                      </span>
                    </div>
                    <div className="mt-4 flex items-end gap-3">
                      <span className="text-4xl font-semibold leading-none tracking-tight tabular-nums text-ink">
                        {row.aqiValue ?? "—"}
                      </span>
                      <span className="pb-0.5">
                        <AqiBadge value={row.aqiValue} category={row.category} size="sm" />
                      </span>
                    </div>
                    {row.reason && <p className="mt-2 text-xs leading-5 text-muted">{row.reason}</p>}
                    <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 border-t border-line pt-3 text-xs">
                      {row.pollutants.map((pollutant) => (
                        <div key={pollutant.parameter} className="flex items-baseline justify-between gap-2">
                          <dt className="text-muted">
                            <Formula name={pollutant.display_name} />
                          </dt>
                          <dd
                            className={`truncate tabular-nums ${pollutant.value === null ? "text-faint" : "font-medium text-ink"}`}
                            title={pollutant.value === null ? undefined : `${pollutant.value} ${pollutant.unit}`}
                          >
                            {pollutant.value === null ? "Unavailable" : `${pollutant.value} ${pollutant.unit}`}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs leading-5 text-muted">{note}</p>
          {series.length > 1 && <CompareCharts cities={series} />}
        </div>
      )}
    </article>
  );
}

export function ForecastPanel({ locationId, timeZone }: { locationId: number; timeZone: string }) {
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [pollutant, setPollutant] = useState("pm25");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/v1/locations/${locationId}/forecast`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("The model forecast is unavailable. Stored station readings are unchanged.");
        return (await response.json()) as Forecast;
      })
      .then((body) => {
        setForecast(body);
        setError("");
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setError(err.message);
      });
    return () => controller.abort();
  }, [locationId]);

  const rows = useMemo(() => {
    if (!forecast) return [];
    return forecast.points
      .filter((point) => point.kind === "air_quality" && point.parameter === pollutant)
      .map((point) => ({
        label: formatWhen(point.forecast_for, timeZone),
        aqi: null,
        pollutant: point.value,
      }));
  }, [forecast, pollutant, timeZone]);
  const selected = POLLUTANTS.find((item) => item.id === pollutant) ?? POLLUTANTS[0];
  const cacheLabel =
    forecast?.cache === "hit" ? "Served from cache" : forecast?.cache === "stale" ? "Last stored model run" : "Fetched from Open-Meteo";

  return (
    <article
      className="relative rounded-3xl border border-dashed p-5 sm:p-6"
      style={{
        borderColor: "color-mix(in srgb, var(--chart-model) 42%, transparent)",
        background: "color-mix(in srgb, var(--chart-model) 5%, var(--surface))",
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl border"
            style={{
              color: "var(--chart-model)",
              borderColor: "color-mix(in srgb, var(--chart-model) 35%, transparent)",
              background: "color-mix(in srgb, var(--chart-model) 12%, transparent)",
            }}
          >
            <Sparkles size={17} />
          </span>
          <div className="min-w-0">
            <h2 className="flex flex-wrap items-center gap-2 text-base font-semibold tracking-tight text-ink">
              Model air-quality forecast
              <span
                className="rounded-full px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em]"
                style={{
                  color: "var(--chart-model)",
                  background: "color-mix(in srgb, var(--chart-model) 14%, transparent)",
                }}
              >
                Model
              </span>
            </h2>
            <p className="mt-0.5 text-xs leading-5 text-muted">
              Separate from station observations. Not an official CPCB AQI.
            </p>
          </div>
        </div>
        <span className="chip text-muted">
          <CalendarClock size={13} />
          {cacheLabel}
        </span>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <span className="eyebrow">Model pollutant</span>
        <Segmented label="Model pollutant" value={pollutant} onChange={setPollutant} options={POLLUTANTS} formula />
      </div>

      <div className="mt-5">
        {error ? (
          <Banner tone="error" role="alert">
            {error}
          </Banner>
        ) : (
          <TrendChart
            rows={rows}
            pollutantName={`${selected.name} model`}
            unit={selected.unit}
            showAqi={false}
            tone="model"
            emptyText="No model values for this pollutant."
            loading={!forecast}
          />
        )}
      </div>
      <p className="mt-3 text-xs leading-5 text-muted">{forecast?.note}</p>
    </article>
  );
}
