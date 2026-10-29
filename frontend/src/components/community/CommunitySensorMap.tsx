"use client";

import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import type { CommunitySensor } from "@/lib/types";

function getSensorColor(sensor: CommunitySensor): string {
  if (!sensor.latest_reading || !sensor.last_seen) return "#9ca3af"; // grey - offline
  
  const lastSeenTime = new Date(sensor.last_seen).getTime();
  const now = Date.now();
  const twoMinutesAgo = now - 2 * 60 * 1000;
  
  if (lastSeenTime < twoMinutesAgo) return "#9ca3af"; // grey - offline
  
  const pm25 = sensor.latest_reading.pm25;
  if (pm25 < 30) return "#22c55e"; // green
  if (pm25 < 60) return "#eab308"; // yellow
  if (pm25 < 100) return "#f97316"; // orange
  return "#ef4444"; // red
}

function sensorIcon(sensor: CommunitySensor, active: boolean) {
  const color = getSensorColor(sensor);
  const label = sensor.latest_reading ? Math.round(sensor.latest_reading.pm25).toString() : "–";
  
  return L.divIcon({
    className: "",
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -16],
    html: `<div class="sensor-pin${active ? " sensor-pin--active" : ""}" style="--pin:${color}">
      <span class="sensor-pin__pulse"></span>
      <span class="sensor-pin__dot">${label}</span>
    </div>`,
  });
}

function FitSensors({ sensors, center }: { sensors: CommunitySensor[]; center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    if (sensors.length === 0) return;
    const bounds = L.latLngBounds([
      center,
      ...sensors.map((sensor) => [sensor.latitude, sensor.longitude] as [number, number]),
    ]);
    map.fitBounds(bounds, { padding: [48, 48], maxZoom: 12, animate: false });
  }, [map, sensors, center]);
  return null;
}

function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) return "Never";
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
  return date.toLocaleString();
}

function getSensorStatus(sensor: CommunitySensor): string {
  if (!sensor.last_seen) return "Offline";
  const lastSeenTime = new Date(sensor.last_seen).getTime();
  const now = Date.now();
  const twoMinutesAgo = now - 2 * 60 * 1000;
  return lastSeenTime < twoMinutesAgo ? "Offline" : "Online";
}

export default function CommunitySensorMap({
  sensors,
  center,
  activeId = null,
  onSelect,
}: {
  sensors: CommunitySensor[];
  center: [number, number];
  activeId?: string | null;
  onSelect?: (id: string) => void;
}) {
  const markers = useRef(new Map<string, L.Marker>());
  const mapRef = useRef<L.Map | null>(null);
  const icons = useMemo(
    () => new Map(sensors.map((sensor) => [sensor.id, sensorIcon(sensor, sensor.id === activeId)])),
    [sensors, activeId],
  );

  useEffect(() => {
    if (activeId === null) return;
    const sensor = sensors.find((item) => item.id === activeId);
    const map = mapRef.current;
    if (!sensor || !map) return;
    map.flyTo([sensor.latitude, sensor.longitude], Math.max(map.getZoom(), 12), { duration: 0.7 });
    markers.current.get(activeId)?.openPopup();
  }, [activeId, sensors]);

  return (
    <MapContainer ref={mapRef} center={center} zoom={11} scrollWheelZoom={false} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitSensors sensors={sensors} center={center} />
      {sensors.map((sensor) => (
        <Marker
          key={sensor.id}
          position={[sensor.latitude, sensor.longitude]}
          icon={icons.get(sensor.id)}
          title={sensor.name}
          ref={(marker) => {
            if (marker) markers.current.set(sensor.id, marker);
            else markers.current.delete(sensor.id);
          }}
          eventHandlers={{ click: () => onSelect?.(sensor.id) }}
        >
          <Popup>
            <div className="min-w-[14rem]">
              <div className="pr-5 text-sm font-semibold leading-5 text-ink">{sensor.name}</div>
              <div className="mt-1 font-mono text-[11px] text-muted">
                {sensor.latitude.toFixed(4)}, {sensor.longitude.toFixed(4)}
              </div>
              <div className="mt-2 text-xs">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 font-medium ${
                    getSensorStatus(sensor) === "Online"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
                  }`}
                >
                  {getSensorStatus(sensor)}
                </span>
              </div>
              {sensor.latest_reading && (
                <ul className="mt-3 space-y-1 text-xs">
                  <li className="flex justify-between gap-6">
                    <span className="text-muted">PM2.5</span>
                    <span className="font-medium tabular-nums text-ink">
                      {sensor.latest_reading.pm25.toFixed(1)}{" "}
                      <span className="font-normal text-muted">µg/m³</span>
                    </span>
                  </li>
                  <li className="flex justify-between gap-6">
                    <span className="text-muted">PM10</span>
                    <span className="font-medium tabular-nums text-ink">
                      {sensor.latest_reading.pm10.toFixed(1)}{" "}
                      <span className="font-normal text-muted">µg/m³</span>
                    </span>
                  </li>
                  {sensor.latest_reading.temperature !== null && (
                    <li className="flex justify-between gap-6">
                      <span className="text-muted">Temperature</span>
                      <span className="font-medium tabular-nums text-ink">
                        {sensor.latest_reading.temperature.toFixed(1)}{" "}
                        <span className="font-normal text-muted">°C</span>
                      </span>
                    </li>
                  )}
                  {sensor.latest_reading.humidity !== null && (
                    <li className="flex justify-between gap-6">
                      <span className="text-muted">Humidity</span>
                      <span className="font-medium tabular-nums text-ink">
                        {sensor.latest_reading.humidity.toFixed(1)}{" "}
                        <span className="font-normal text-muted">%</span>
                      </span>
                    </li>
                  )}
                </ul>
              )}
              <div className="mt-3 border-t border-line pt-2.5 text-[11px] leading-4 text-muted">
                Last seen: {formatTimestamp(sensor.last_seen)}
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
