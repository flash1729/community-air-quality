"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  ACTIVE_DOT,
  ChartTooltip,
  CURSOR_BAND,
  CURSOR_LINE,
  GRID_STROKE,
  TIME_AXIS,
  axisTick,
  tickNumber,
} from "@/components/chart-kit";
import { Formula, Segmented } from "@/components/ui";
import { formatNumber, formatWhen } from "@/lib/format";
import type { HistoryPoint } from "@/lib/types";

const METRICS = [
  { id: "aqi", name: "AQI", unit: "AQI" },
  { id: "pm25", name: "PM2.5", unit: "µg/m³" },
  { id: "pm10", name: "PM10", unit: "µg/m³" },
  { id: "no2", name: "NO2", unit: "µg/m³" },
  { id: "so2", name: "SO2", unit: "µg/m³" },
  { id: "co", name: "CO", unit: "mg/m³" },
  { id: "o3", name: "O3", unit: "µg/m³" },
];

export const CITY_COLORS = ["var(--city-1)", "var(--city-2)", "var(--city-3)", "var(--city-4)"];

export type ComparedSeries = {
  id: number;
  name: string;
  aqiValue: number | null;
  pollutantValues: Record<string, number | null>;
  points: HistoryPoint[];
};

type TipPayload = { name?: string; value?: unknown; color?: string }[];

export function CompareCharts({ cities }: { cities: ComparedSeries[] }) {
  const [metric, setMetric] = useState("aqi");
  const [hidden, setHidden] = useState<string[]>([]);
  const selected = METRICS.find((item) => item.id === metric) ?? METRICS[0];
  const visible = cities.filter((city) => !hidden.includes(city.name));

  const bars = useMemo(
    () =>
      cities.map((city) => ({
        name: city.name,
        value: reading(city, metric),
      })),
    [cities, metric],
  );

  const lines = useMemo(() => alignHours(cities, metric), [cities, metric]);
  const digits = metric === "co" ? 2 : metric === "aqi" ? 0 : 1;

  function toggleCity(name: string) {
    setHidden((current) => (current.includes(name) ? current.filter((item) => item !== name) : [...current, name]));
  }

  return (
    <div className="mt-6 space-y-5 border-t border-line pt-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Comparison charts</h3>
          <p className="mt-0.5 text-xs text-muted">Hover a point for the value. Select a city in the legend to hide it.</p>
        </div>
        <Segmented label="Show" value={metric} onChange={setMetric} options={METRICS} formula />
      </div>

      <ul className="flex flex-wrap gap-2" aria-label="Cities shown in the charts">
        {cities.map((city, index) => {
          const shown = !hidden.includes(city.name);
          return (
            <li key={city.id}>
              <button
                type="button"
                aria-pressed={shown}
                onClick={() => toggleCity(city.name)}
                className={`chip transition duration-200 hover:border-line-strong ${shown ? "" : "opacity-45"}`}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: CITY_COLORS[index % CITY_COLORS.length] }}
                />
                <span className={shown ? "" : "line-through"}>{city.name}</span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.4fr)]">
        <figure className="rounded-2xl border border-line bg-surface-2 p-4">
          <figcaption className="eyebrow mb-3">
            Latest <Formula name={selected.name} />
          </figcaption>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bars} margin={{ top: 22, right: 4, left: 0, bottom: 0 }} barCategoryGap="28%">
                <CartesianGrid stroke={GRID_STROKE} vertical={false} />
                <XAxis dataKey="name" tick={axisTick()} tickLine={false} axisLine={false} tickMargin={10} />
                <YAxis tick={axisTick()} tickFormatter={tickNumber} tickLine={false} axisLine={false} width={44} />
                <Tooltip
                  cursor={CURSOR_BAND}
                  content={(props) => (
                    <ChartTooltip
                      active={props.active}
                      label={props.label}
                      payload={(props.payload ?? []).map((item) => ({
                        name: selected.name,
                        value: item.value,
                        color: CITY_COLORS[Math.max(0, bars.findIndex((bar) => bar.name === props.label)) % CITY_COLORS.length],
                      }))}
                      format={(value) => withUnit(displayValue(value, digits), selected)}
                    />
                  )}
                />
                <Bar dataKey="value" name={selected.name} radius={[10, 10, 3, 3]} maxBarSize={64} animationDuration={700}>
                  {bars.map((bar, index) => (
                    <Cell
                      key={bar.name}
                      fill={CITY_COLORS[index % CITY_COLORS.length]}
                      fillOpacity={hidden.includes(bar.name) ? 0.2 : 0.95}
                    />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="top"
                    offset={8}
                    formatter={(value: unknown) =>
                      value === null || value === undefined ? "" : displayValue(value, digits)
                    }
                    style={{ fill: "rgb(var(--ink))", fontSize: 11, fontWeight: 600 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </figure>

        <figure className="rounded-2xl border border-line bg-surface-2 p-4">
          <figcaption className="eyebrow mb-3">
            Hourly <Formula name={selected.name} /> · UTC
          </figcaption>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lines} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={GRID_STROKE} vertical={false} />
                <XAxis {...TIME_AXIS} />
                <YAxis tick={axisTick()} tickFormatter={tickNumber} tickLine={false} axisLine={false} width={44} />
                <Tooltip
                  cursor={CURSOR_LINE}
                  content={(props) => (
                    <ChartTooltip
                      active={props.active}
                      label={props.label}
                      payload={props.payload as unknown as TipPayload}
                      format={(value) => withUnit(displayValue(value, digits), selected)}
                    />
                  )}
                />
                {visible.map((city) => (
                  <Line
                    key={city.id}
                    type="monotone"
                    dataKey={city.name}
                    name={city.name}
                    stroke={CITY_COLORS[cities.findIndex((item) => item.id === city.id) % CITY_COLORS.length]}
                    strokeWidth={2.2}
                    dot={false}
                    activeDot={ACTIVE_DOT}
                    connectNulls={false}
                    animationDuration={900}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </figure>
      </div>

      <p className="text-xs leading-5 text-muted">
        Latest {selected.name} is the bar chart. The lines are hourly station observations in UTC. Empty stretches are missing hours, not zero.{" "}
        {selected.id === "aqi" ? "AQI is the rolling CPCB value and stays blank until a city has enough coverage." : `${selected.name} is shown in ${selected.unit}.`}
      </p>
    </div>
  );
}

function reading(city: ComparedSeries, metric: string): number | null {
  if (metric === "aqi") return city.aqiValue;
  return city.pollutantValues[metric] ?? null;
}

function displayValue(value: unknown, digits: number): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Unavailable";
  return digits === 0 ? String(Math.round(Number(value))) : formatNumber(Number(value), digits);
}

function withUnit(text: string, metric: { id: string; unit: string }): string {
  if (text === "Unavailable" || metric.id === "aqi") return text;
  return `${text} ${metric.unit}`;
}

function alignHours(cities: ComparedSeries[], metric: string) {
  const stamps = new Map<string, { label: string; order: number }>();
  for (const city of cities) {
    for (const point of city.points) {
      const order = Date.parse(point.measured_at);
      if (!Number.isFinite(order)) continue;
      const key = new Date(order).toISOString();
      if (!stamps.has(key)) stamps.set(key, { label: formatWhen(point.measured_at, "UTC"), order });
    }
  }
  return [...stamps.entries()]
    .sort((left, right) => left[1].order - right[1].order)
    .map(([key, stamp]) => {
      const row: Record<string, string | number | null> = { label: stamp.label };
      for (const city of cities) {
        const point = city.points.find((item) => new Date(item.measured_at).toISOString() === key);
        if (!point) {
          row[city.name] = null;
          continue;
        }
        row[city.name] = metric === "aqi" ? point.aqi : (point.pollutants[metric] ?? null);
      }
      return row;
    });
}
