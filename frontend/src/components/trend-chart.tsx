"use client";

import { useId } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  ACTIVE_DOT,
  ChartTooltip,
  CURSOR_LINE,
  EmptyChart,
  GRID_STROKE,
  LegendKey,
  TIME_AXIS,
  axisTick,
  isMissing,
  tickNumber,
} from "@/components/chart-kit";
import { Formula } from "@/components/ui";
import { formatNumber } from "@/lib/format";

export type ChartRow = {
  label: string;
  aqi: number | null;
  pollutant: number | null;
};

export function TrendChart({
  rows,
  pollutantName,
  unit,
  showAqi = true,
  tone = "observed",
  emptyText = "No readings stored for this window.",
  loading = false,
}: {
  rows: ChartRow[];
  pollutantName: string;
  unit: string;
  showAqi?: boolean;
  tone?: "observed" | "model";
  emptyText?: string;
  loading?: boolean;
}) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const aqiColor = "var(--chart-aqi)";
  const lineColor = tone === "model" ? "var(--chart-model)" : "var(--chart-pollutant)";
  const hasAqi = showAqi && rows.some((row) => row.aqi !== null);
  const hasPollutant = rows.some((row) => row.pollutant !== null);
  const [formulaName, ...suffix] = pollutantName.split(" ");

  return (
    <div>
      <ul className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted">
        {showAqi && (
          <li>
            <LegendKey color={aqiColor}>
              <span className="font-medium text-ink">AQI</span> · left axis
              {!hasAqi && !loading && " · no values in this window"}
            </LegendKey>
          </li>
        )}
        <li>
          <LegendKey color={lineColor} dashed={tone === "model"}>
            <span className="font-medium text-ink">
              <Formula name={formulaName} />
              {suffix.length > 0 ? ` ${suffix.join(" ")}` : ""}
            </span>{" "}
            · {unit}
            {showAqi ? " · right axis" : ""}
            {!hasPollutant && !loading && " · no values in this window"}
          </LegendKey>
        </li>
      </ul>

      <div className="relative h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: showAqi ? 4 : 28, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`aqi-${id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" style={{ stopColor: aqiColor, stopOpacity: 0.34 }} />
                <stop offset="100%" style={{ stopColor: aqiColor, stopOpacity: 0 }} />
              </linearGradient>
              <linearGradient id={`line-${id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" style={{ stopColor: lineColor, stopOpacity: 0.3 }} />
                <stop offset="100%" style={{ stopColor: lineColor, stopOpacity: 0 }} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={GRID_STROKE} vertical={false} />
            <XAxis {...TIME_AXIS} />
            {showAqi && (
              <YAxis
                yAxisId="aqi"
                tick={axisTick(aqiColor)}
                tickFormatter={tickNumber}
                tickLine={false}
                axisLine={false}
                width={42}
              />
            )}
            <YAxis
              yAxisId="pollutant"
              orientation={showAqi ? "right" : "left"}
              tick={axisTick(showAqi ? lineColor : undefined)}
              tickFormatter={tickNumber}
              tickLine={false}
              axisLine={false}
              width={46}
            />
            <Tooltip
              cursor={CURSOR_LINE}
              content={(props) => (
                <ChartTooltip
                  active={props.active}
                  label={props.label}
                  payload={props.payload as unknown as { name?: string; value?: unknown; color?: string }[]}
                  format={(value, name) => {
                    if (isMissing(value)) return "Unavailable";
                    if (name === "AQI") return String(value);
                    return `${formatNumber(Number(value), unit === "mg/m³" ? 2 : 1)} ${unit}`;
                  }}
                />
              )}
            />
            {showAqi && (
              <Area
                yAxisId="aqi"
                type="monotone"
                dataKey="aqi"
                name="AQI"
                stroke={aqiColor}
                strokeWidth={2.2}
                fill={`url(#aqi-${id})`}
                dot={false}
                activeDot={ACTIVE_DOT}
                connectNulls={false}
                animationDuration={900}
              />
            )}
            {showAqi ? (
              <Line
                yAxisId="pollutant"
                type="monotone"
                dataKey="pollutant"
                name={pollutantName}
                stroke={lineColor}
                strokeWidth={2.2}
                dot={false}
                activeDot={ACTIVE_DOT}
                connectNulls={false}
                animationDuration={900}
              />
            ) : (
              <Area
                yAxisId="pollutant"
                type="monotone"
                dataKey="pollutant"
                name={pollutantName}
                stroke={lineColor}
                strokeWidth={2.2}
                strokeDasharray={tone === "model" ? "6 4" : undefined}
                fill={`url(#line-${id})`}
                dot={false}
                activeDot={ACTIVE_DOT}
                connectNulls={false}
                animationDuration={900}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
        {!hasAqi && !hasPollutant && <EmptyChart>{loading ? "Loading…" : emptyText}</EmptyChart>}
      </div>
    </div>
  );
}
