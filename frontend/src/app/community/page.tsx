"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

import AddSensorModal from "@/components/community/AddSensorModal";
import SensorDetails from "@/components/community/SensorDetails";
import SensorHistory from "@/components/community/SensorHistory";
import type { CommunitySensor } from "@/lib/types";

// Dynamic import for map to avoid SSR issues with Leaflet
const CommunitySensorMap = dynamic(() => import("@/components/community/CommunitySensorMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-surface-2 text-sm text-muted">
      Loading map...
    </div>
  ),
});

export default function CommunityPage() {
  const [sensors, setSensors] = useState<CommunitySensor[]>([]);
  const [selectedSensorId, setSelectedSensorId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const selectedSensor = sensors.find((s) => s.id === selectedSensorId) || null;

  // Fetch sensors from backend
  const fetchSensors = async () => {
    try {
      const response = await fetch("/api/v1/community/sensors");
      if (!response.ok) {
        throw new Error(`Failed to fetch sensors: ${response.statusText}`);
      }
      const data = await response.json();
      setSensors(data);
    } catch (err) {
      console.error("Error fetching sensors:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSensors();

    // Poll every 5 seconds
    const interval = setInterval(fetchSensors, 5000);

    // Cleanup on unmount
    return () => clearInterval(interval);
  }, []);

  const handleSensorAdded = () => {
    // Immediately refresh sensor list when a new sensor is registered
    fetchSensors();
  };

  // Calculate metrics
  const totalSensors = sensors.length;
  const onlineSensors = sensors.filter((sensor) => {
    if (!sensor.last_seen) return false;
    const lastSeenTime = new Date(sensor.last_seen).getTime();
    const now = Date.now();
    const twoMinutesAgo = now - 2 * 60 * 1000;
    return lastSeenTime >= twoMinutesAgo;
  }).length;
  const offlineSensors = totalSensors - onlineSensors;
  const sensorsWithReadings = sensors.filter((s) => s.latest_reading !== null).length;

  return (
    <main id="main" className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Community Sensor Network</h1>
          <p className="mt-1 text-sm text-muted">
            Real-time air quality measurements from community-operated sensors across Bengaluru
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Sensor
        </button>
      </div>

      {/* Metrics Dashboard */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-muted">Total Sensors</div>
          <div className="mt-2 text-2xl font-bold tabular-nums text-ink">{totalSensors}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-muted">Online</div>
          <div className="mt-2 text-2xl font-bold tabular-nums text-green-600 dark:text-green-400">
            {onlineSensors}
          </div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-muted">Offline</div>
          <div className="mt-2 text-2xl font-bold tabular-nums text-gray-500">{offlineSensors}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-muted">Latest Readings</div>
          <div className="mt-2 text-2xl font-bold tabular-nums text-ink">{sensorsWithReadings}</div>
        </div>
      </div>

      {/* Map and Details Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Map Section */}
        <div className="lg:col-span-3">
          <div className="h-[500px] overflow-hidden rounded-xl border border-line bg-surface-2 lg:h-[600px]">
            {loading ? (
              <div className="flex h-full items-center justify-center text-sm text-muted">
                Loading sensors...
              </div>
            ) : sensors.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted">
                No sensors found. Run the seed script to create sensors.
              </div>
            ) : (
              <CommunitySensorMap
                sensors={sensors}
                center={[12.9716, 77.5946]} // Bengaluru center
                activeId={selectedSensorId}
                onSelect={setSelectedSensorId}
              />
            )}
          </div>
        </div>

        {/* Details Panel */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            {selectedSensor ? (
              <>
                <SensorDetails sensor={selectedSensor} />
                <SensorHistory sensorId={selectedSensorId} />
              </>
            ) : (
              <div className="flex h-[500px] items-center justify-center rounded-xl border border-line bg-surface-2 text-sm text-muted lg:h-[600px]">
                Select a sensor on the map to view details
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Sensor Modal */}
      <AddSensorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleSensorAdded}
      />
    </main>
  );
}
