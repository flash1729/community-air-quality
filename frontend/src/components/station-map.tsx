"use client";

import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { AqiBadge, Formula } from "@/components/ui";
import { categoryStyle } from "@/lib/format";
import type { Station } from "@/lib/types";

function pinIcon(station: Station, active: boolean) {
  const style = categoryStyle(station.aqi.category);
  const label = station.aqi.available && station.aqi.value !== null ? String(station.aqi.value) : "–";
  return L.divIcon({
    className: "",
    iconSize: [38, 38],
    iconAnchor: [19, 19],
    popupAnchor: [0, -18],
    html: `<div class="aqi-pin${active ? " aqi-pin--active" : ""}" style="--pin:${style.solid};--pin-on:${style.on}"><span class="aqi-pin__pulse"></span><span class="aqi-pin__dot">${label}</span></div>`,
  });
}

/** Frames every station once, so none start outside the view. */
function FitStations({ stations, center }: { stations: Station[]; center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    if (stations.length === 0) return;
    const bounds = L.latLngBounds([center, ...stations.map((station) => [station.latitude, station.longitude] as [number, number])]);
    map.fitBounds(bounds, { padding: [48, 48], maxZoom: 12, animate: false });
    // Only on mount: the map is re-keyed when the city or filter changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);
  return null;
}

export default function StationMap({
  stations,
  center,
  activeId = null,
  onSelect,
}: {
  stations: Station[];
  center: [number, number];
  activeId?: number | null;
  onSelect?: (id: number) => void;
}) {
  const markers = useRef(new Map<number, L.Marker>());
  const mapRef = useRef<L.Map | null>(null);
  const icons = useMemo(
    () => new Map(stations.map((station) => [station.id, pinIcon(station, station.id === activeId)])),
    [stations, activeId],
  );

  useEffect(() => {
    if (activeId === null) return;
    const station = stations.find((item) => item.id === activeId);
    const map = mapRef.current;
    if (!station || !map) return;
    map.flyTo([station.latitude, station.longitude], Math.max(map.getZoom(), 12), { duration: 0.7 });
    markers.current.get(activeId)?.openPopup();
  }, [activeId, stations]);

  return (
    <MapContainer ref={mapRef} center={center} zoom={11} scrollWheelZoom={false} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitStations stations={stations} center={center} />
      {stations.map((station) => (
        <Marker
          key={station.id}
          position={[station.latitude, station.longitude]}
          icon={icons.get(station.id)}
          title={station.name}
          ref={(marker) => {
            if (marker) markers.current.set(station.id, marker);
            else markers.current.delete(station.id);
          }}
          eventHandlers={{ click: () => onSelect?.(station.id) }}
        >
          <Popup>
            <div className="min-w-[12rem]">
              <div className="pr-5 text-sm font-semibold leading-5 text-ink">{station.name}</div>
              <div className="mt-1 font-mono text-[11px] text-muted">
                {station.latitude.toFixed(4)}, {station.longitude.toFixed(4)}
              </div>
              <div className="mt-3">
                <AqiBadge value={station.aqi.available ? station.aqi.value : null} category={station.aqi.category} />
              </div>
              <ul className="mt-3 space-y-1 text-xs">
                {station.pollutants
                  .filter((item) => item.value !== null)
                  .map((item) => (
                    <li key={item.parameter} className="flex justify-between gap-6">
                      <span className="text-muted">
                        <Formula name={item.display_name} />
                      </span>
                      <span className="font-medium tabular-nums text-ink">
                        {item.value} <span className="font-normal text-muted">{item.unit}</span>
                      </span>
                    </li>
                  ))}
              </ul>
              <div className="mt-3 border-t border-line pt-2.5 text-[11px] leading-4 text-muted">
                Monitoring station. Not a modelled grid cell.
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
