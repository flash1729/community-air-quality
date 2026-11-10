"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Plus } from "lucide-react";

import AddSensorModal from "@/components/community/AddSensorModal";
import SensorDetails from "@/components/community/SensorDetails";
import SensorHistory from "@/components/community/SensorHistory";
import { SiteHeader } from "@/components/site-header";
import { Ambient } from "@/components/ui";
import type { CommunitySensor } from "@/lib/types";

// Stable reference so the map is not re-fitted or re-centered on every poll.
const BENGALURU_CENTER: [number, number] = [12.9716, 77.5946];

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
    <div className="min-h-screen">
      <Ambient />
      <SiteHeader />
      <main id="main" className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Community Sensor Network</h1>
            <p className="mt-1 text-sm text-muted">
              Real-time air quality measurements from community-operated sensors across Bengaluru
            </p>
          </div>
          <button type="button" onClick={() => setIsModalOpen(true)} className="btn btn-primary">
            <Plus size={16} />
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
            <div className="isolate h-[500px] overflow-hidden rounded-xl border border-line bg-surface-2 lg:h-[600px]">
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
                  center={BENGALURU_CENTER}
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
    </div>
  );
}
