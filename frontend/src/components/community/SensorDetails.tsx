"use client";

import type { CommunitySensor } from "@/lib/types";

function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) return "Never";
  const date = new Date(timestamp);
  return date.toLocaleString();
}

function getSensorStatus(sensor: CommunitySensor): { label: string; color: string } {
  if (!sensor.last_seen) return { label: "Offline", color: "gray" };
  const lastSeenTime = new Date(sensor.last_seen).getTime();
  const now = Date.now();
  const twoMinutesAgo = now - 2 * 60 * 1000;
  
  if (lastSeenTime < twoMinutesAgo) {
    return { label: "Offline", color: "gray" };
  }
  return { label: "Online", color: "green" };
}

export default function SensorDetails({ sensor }: { sensor: CommunitySensor }) {
  const status = getSensorStatus(sensor);
  
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <h3 className="text-sm font-semibold text-ink">{sensor.name}</h3>
        <div className="mt-2 space-y-1.5 text-xs text-muted">
          <div className="flex justify-between">
            <span>Sensor ID:</span>
            <span className="font-mono text-ink">{sensor.id}</span>
          </div>
          <div className="flex justify-between">
            <span>Type:</span>
            <span className="text-ink">{sensor.sensor_type}</span>
          </div>
          {sensor.source === "contributed" && (
            <>
              <div className="flex justify-between">
                <span>Source:</span>
                <span className="inline-block rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-medium dark:bg-blue-900/30 dark:text-blue-400">
                  Community Contributed
                </span>
              </div>
              {sensor.hardware_id && (
                <div className="flex justify-between">
                  <span>Hardware ID:</span>
                  <span className="font-mono text-ink">{sensor.hardware_id}</span>
                </div>
              )}
              {sensor.hardware_model && (
                <div className="flex justify-between">
                  <span>Hardware Model:</span>
                  <span className="text-ink">{sensor.hardware_model}</span>
                </div>
              )}
              {sensor.contributor_name && (
                <div className="flex justify-between">
                  <span>Contributor:</span>
                  <span className="text-ink">{sensor.contributor_name}</span>
                </div>
              )}
            </>
          )}
          <div className="flex justify-between">
            <span>Location:</span>
            {sensor.latitude !== null && sensor.longitude !== null ? (
              <span className="font-mono text-ink">
                {sensor.latitude.toFixed(4)}, {sensor.longitude.toFixed(4)}
              </span>
            ) : (
              <span className="italic text-muted">Awaiting first data</span>
            )}
          </div>
          <div className="flex justify-between">
            <span>Status:</span>
            <span
              className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${
                status.color === "green"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
              }`}
            >
              {status.label}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Last seen:</span>
            <span className="text-ink">{formatTimestamp(sensor.last_seen)}</span>
          </div>
        </div>
      </div>

      {sensor.latest_reading && (
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <h3 className="text-sm font-semibold text-ink">Latest Reading</h3>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-surface-solid p-3">
              <div className="text-[10px] uppercase tracking-wider text-muted">PM2.5</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-ink">
                {sensor.latest_reading.pm25.toFixed(1)}
              </div>
              <div className="text-[10px] text-muted">µg/m³</div>
            </div>
            <div className="rounded-lg bg-surface-solid p-3">
              <div className="text-[10px] uppercase tracking-wider text-muted">PM10</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-ink">
                {sensor.latest_reading.pm10.toFixed(1)}
              </div>
              <div className="text-[10px] text-muted">µg/m³</div>
            </div>
            {sensor.latest_reading.temperature !== null && (
              <div className="rounded-lg bg-surface-solid p-3">
                <div className="text-[10px] uppercase tracking-wider text-muted">Temperature</div>
                <div className="mt-1 text-xl font-semibold tabular-nums text-ink">
                  {sensor.latest_reading.temperature.toFixed(1)}
                </div>
                <div className="text-[10px] text-muted">°C</div>
              </div>
            )}
            {sensor.latest_reading.humidity !== null && (
              <div className="rounded-lg bg-surface-solid p-3">
                <div className="text-[10px] uppercase tracking-wider text-muted">Humidity</div>
                <div className="mt-1 text-xl font-semibold tabular-nums text-ink">
                  {sensor.latest_reading.humidity.toFixed(1)}
                </div>
                <div className="text-[10px] text-muted">%</div>
              </div>
            )}
          </div>
          <div className="mt-3 text-[11px] text-muted">
            Recorded: {formatTimestamp(sensor.latest_reading.recorded_at)}
          </div>
        </div>
      )}
    </div>
  );
}
