"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  ACTIVE_DOT,
  ChartTooltip,
  CURSOR_LINE,
  EmptyChart,
  GRID_STROKE,
  LegendKey,
  axisTick,
  isMissing,
  tickNumber,
} from "@/components/chart-kit";
import { formatNumber } from "@/lib/format";
import type { CommunitySensorReading } from "@/lib/types";

type ChartRow = {
  label: string;
  pm25: number | null;
  pm10: number | null;
};

export default function SensorHistory({ sensorId }: { sensorId: string | null }) {
  const [readings, setReadings] = useState<CommunitySensorReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sensorId) {
      setReadings([]);
      return;
    }

    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/v1/community/sensors/${sensorId}/readings?limit=50`
        );
        if (!response.ok) {
          throw new Error(`Failed to fetch readings: ${response.statusText}`);
        }
        const data = await response.json();
        setReadings(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch history");
        setReadings([]);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [sensorId]);

  if (!sensorId) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl border border-line bg-surface-2 text-sm text-muted">
        Select a sensor on the map to view its history
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl border border-line bg-surface-2 text-sm text-muted">
        Loading history...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl border border-line bg-surface-2 text-sm text-red-500">
        {error}
      </div>
    );
  }

  const chartData: ChartRow[] = readings.map((reading) => ({
    label: new Date(reading.recorded_at).toLocaleTimeString(),
    pm25: reading.pm25,
    pm10: reading.pm10,
  })).reverse(); // Reverse to show oldest to newest

  const hasPm25 = chartData.some((row) => row.pm25 !== null);
  const hasPm10 = chartData.some((row) => row.pm10 !== null);

  return (
    <div className="rounded-xl border border-line bg-surface-2 p-4">
      <h3 className="text-sm font-semibold text-ink">Historical Readings</h3>
      
      <ul className="mb-4 mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted">
        <li>
          <LegendKey color="var(--chart-pollutant)">
            <span className="font-medium text-ink">PM2.5</span> · µg/m³
            {!hasPm25 && !loading && " · no values"}
          </LegendKey>
        </li>
        <li>
          <LegendKey color="#f97316">
            <span className="font-medium text-ink">PM10</span> · µg/m³
            {!hasPm10 && !loading && " · no values"}
          </LegendKey>
        </li>
      </ul>

      <div className="relative h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={GRID_STROKE} vertical={false} />
            <XAxis
              dataKey="label"
              tick={axisTick()}
              tickLine={false}
              axisLine={false}
              height={40}
              angle={-45}
              textAnchor="end"
              interval="preserveStartEnd"
            />
            <YAxis
              tick={axisTick()}
              tickFormatter={tickNumber}
              tickLine={false}
              axisLine={false}
              width={46}
              label={{ value: "µg/m³", angle: -90, position: "insideLeft", style: { textAnchor: "middle" } }}
            />
            <Tooltip
              cursor={CURSOR_LINE}
              content={(props) => (
                <ChartTooltip
                  active={props.active}
                  label={props.label}
                  payload={props.payload as unknown as { name?: string; value?: unknown; color?: string }[]}
                  format={(value) => {
                    if (isMissing(value)) return "Unavailable";
                    return `${formatNumber(Number(value), 1)} µg/m³`;
                  }}
                />
              )}
            />
            <Line
              type="monotone"
              dataKey="pm25"
              name="PM2.5"
              stroke="var(--chart-pollutant)"
              strokeWidth={2.2}
              dot={false}
              activeDot={ACTIVE_DOT}
              connectNulls={false}
              animationDuration={900}
            />
            <Line
              type="monotone"
              dataKey="pm10"
              name="PM10"
              stroke="#f97316"
              strokeWidth={2.2}
              dot={false}
              activeDot={ACTIVE_DOT}
              connectNulls={false}
              animationDuration={900}
            />
          </LineChart>
        </ResponsiveContainer>
        {!hasPm25 && !hasPm10 && (
          <EmptyChart>{loading ? "Loading…" : "No readings available for this sensor."}</EmptyChart>
        )}
      </div>
    </div>
  );
}
