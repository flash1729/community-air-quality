"""
Virtual Sensor Simulator for Community Air Quality Monitoring

Run from backend/ with venv active: 
  python -m app.simulator.virtual_sensors

Requires backend API running on --api-url. Reads tokens from --tokens-file and
reloads it every round, so newly provisioned sensors start reporting without a
restart. Sensors with no entry in --locations-file get a random Bengaluru
location, which is saved back to that file.
Ctrl+C to stop.

Examples:
  python -m app.simulator.virtual_sensors --api-url http://localhost:8001
  python -m app.simulator.virtual_sensors --spike SENSOR_001 --duration 60
  python -m app.simulator.virtual_sensors --disconnect SENSOR_002
  python -m app.simulator.virtual_sensors --reconnect SENSOR_002
"""

import json
import time
import random
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from app.simulator.provisioning import write_json_atomic


class VirtualSensor:
    """Represents a virtual IoT air quality sensor.
    
    This class simulates stationary sensors (e.g., home monitors, school installations)
    that report the same geographical coordinates with every reading. Mobile sensors
    that track changing locations are out of scope for this implementation.
    """
    
    def __init__(
        self, 
        sensor_id: str, 
        name: str,
        token: str, 
        latitude: float, 
        longitude: float
    ):
        self.sensor_id = sensor_id
        self.name = name
        self.token = token
        self.latitude = latitude
        self.longitude = longitude
        
        # Initialize with random but realistic baseline values
        self.pm25 = random.uniform(20, 80)
        self.pm10 = self.pm25 * random.uniform(1.5, 2.0)
        self.temperature = random.uniform(22, 30)
        self.humidity = random.uniform(40, 70)
        
        self.sequence_number = 1
        self.active = True
        self.last_spike_time: Optional[float] = None
        self.spike_end_time: Optional[float] = None
        self.original_pm25: Optional[float] = None
        
    def generate_reading(self) -> Dict:
        """Generate next reading with gradual changes."""
        # Gradually adjust PM2.5 by +/- 5
        change = random.uniform(-5, 5)
        self.pm25 = max(10, min(120, self.pm25 + change))
        
        # PM10 is typically 1.3-2.0 times PM2.5
        self.pm10 = self.pm25 * random.uniform(1.3, 2.0)
        
        # Temperature gradual change
        temp_change = random.uniform(-1, 1)
        self.temperature = max(22, min(36, self.temperature + temp_change))
        
        # Humidity gradual change
        humidity_change = random.uniform(-3, 3)
        self.humidity = max(35, min(85, self.humidity + humidity_change))
        
        # Build reading payload with coordinates
        reading = {
            "sensor_id": self.sensor_id,
            "sequence_number": self.sequence_number,
            "pm25": round(self.pm25, 2),
            "pm10": round(self.pm10, 2),
            "temperature": round(self.temperature, 2),
            "humidity": round(self.humidity, 2),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.sequence_number += 1
        return reading
    
    def submit_reading(self, api_base_url: str) -> bool:
        """Submit reading to backend API. Returns True on success."""
        if not self.active:
            return False
            
        try:
            reading = self.generate_reading()
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{api_base_url}/api/v1/community/sensors/readings"
            response = requests.post(url, json=reading, headers=headers, timeout=5)
            
            if response.status_code == 201:
                print(f"✓ {self.sensor_id} seq={reading['sequence_number']} "
                      f"PM2.5={reading['pm25']} status={response.status_code}")
                return True
            else:
                print(f"✗ {self.sensor_id} seq={reading['sequence_number']} "
                      f"status={response.status_code} error={response.text[:100]}")
                return False
                
        except requests.RequestException as e:
            print(f"✗ {self.sensor_id} seq={self.sequence_number} "
                  f"error={type(e).__name__}: {str(e)[:80]}")
            return False
    
    def trigger_spike(self, duration_seconds: int):
        """Trigger a pollution spike for specified duration."""
        current_time = time.time()
        
        # Check if already in spike
        if self.spike_end_time and current_time < self.spike_end_time:
            print(f"⚠ {self.sensor_id} already in spike, ignoring new spike request")
            return
            
        # Save original PM2.5 and apply spike
        self.original_pm25 = self.pm25
        spike_amount = random.uniform(40, 80)
        self.pm25 = min(120, self.pm25 + spike_amount)
        
        self.last_spike_time = current_time
        self.spike_end_time = current_time + duration_seconds
        
        print(f"🔥 {self.sensor_id} SPIKE triggered: PM2.5 {self.original_pm25:.1f} → {self.pm25:.1f} "
              f"for {duration_seconds}s")
    
    def check_spike_expiry(self):
        """Check if spike has expired and restore normal levels."""
        if self.spike_end_time and time.time() >= self.spike_end_time:
            if self.original_pm25 is not None:
                print(f"✓ {self.sensor_id} SPIKE ended, restoring PM2.5 to ~{self.original_pm25:.1f}")
                self.pm25 = self.original_pm25
                self.original_pm25 = None
            self.spike_end_time = None


# Rough Bengaluru bounding box used to place simulated devices that have no
# configured location yet.
BENGALURU_BOUNDS = {"lat_min": 12.85, "lat_max": 13.10, "lon_min": 77.50, "lon_max": 77.75}
# Keep new devices at least ~500 m (in degrees) from any existing location.
MIN_SEPARATION_DEG = 0.005


def random_bengaluru_location(taken: List[Tuple[float, float]], rng: random.Random = random) -> Dict[str, float]:
    """Pick a random point inside Bengaluru that is not on top of an existing sensor."""
    candidate = None
    for _ in range(200):
        lat = round(rng.uniform(BENGALURU_BOUNDS["lat_min"], BENGALURU_BOUNDS["lat_max"]), 4)
        lon = round(rng.uniform(BENGALURU_BOUNDS["lon_min"], BENGALURU_BOUNDS["lon_max"]), 4)
        candidate = {"latitude": lat, "longitude": lon}
        if all(abs(lat - t_lat) >= MIN_SEPARATION_DEG or abs(lon - t_lon) >= MIN_SEPARATION_DEG for t_lat, t_lon in taken):
            return candidate
    return candidate


def _read_json(path: Path) -> Dict:
    """Read a JSON object from disk; a missing or half-written file reads as empty."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _fetch_sensor_metadata(api_base_url: str) -> Optional[Dict[str, Dict]]:
    """Return sensors by ID from the backend, or None if it cannot be reached."""
    try:
        response = requests.get(f"{api_base_url}/api/v1/community/sensors", timeout=10)
        response.raise_for_status()
        return {s["id"]: s for s in response.json()}
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        print(f"⚠ Could not fetch sensor metadata from API: {type(e).__name__}: {str(e)[:80]}")
        return None


def sync_sensors(
    sensors: Dict[str, VirtualSensor],
    tokens_path: Path,
    locations_path: Path,
    api_base_url: str,
    rng: random.Random = random,
) -> Dict[str, VirtualSensor]:
    """Reload the tokens and locations files and start/stop virtual devices to match.

    Each device keeps its own location. A device without one gets, in order: its
    entry in the locations file, the location the backend already holds for it,
    or a new random point inside Bengaluru. New locations are written back to the
    locations file so a device stays put across simulator restarts.
    """
    tokens = _read_json(tokens_path)
    locations = _read_json(locations_path)

    for sensor_id in list(sensors):
        if sensor_id not in tokens:
            print(f"⏹ {sensor_id} removed from tokens file, stopping")
            del sensors[sensor_id]
    for sensor_id, token in tokens.items():
        if sensor_id in sensors:
            sensors[sensor_id].token = token

    new_ids = [sensor_id for sensor_id in tokens if sensor_id not in sensors]
    if not new_ids:
        return sensors

    metadata = _fetch_sensor_metadata(api_base_url)
    if metadata is None:
        # Wait for the backend so new devices resume after its last sequence number.
        print(f"⏳ Backend not reachable, will start {len(new_ids)} new sensor(s) next round")
        return sensors
    taken = [(loc["latitude"], loc["longitude"]) for loc in locations.values()]
    taken += [(s["latitude"], s["longitude"]) for s in metadata.values() if s.get("latitude") is not None and s.get("longitude") is not None]
    locations_changed = False

    for sensor_id in new_ids:
        meta = metadata.get(sensor_id, {})
        location = locations.get(sensor_id)
        if location is None:
            if meta.get("latitude") is not None and meta.get("longitude") is not None:
                location = {"latitude": meta["latitude"], "longitude": meta["longitude"]}
            else:
                location = random_bengaluru_location(taken, rng)
                print(f"📍 {sensor_id} assigned random Bengaluru location {location['latitude']}, {location['longitude']}")
            locations[sensor_id] = location
            taken.append((location["latitude"], location["longitude"]))
            locations_changed = True

        sensor = VirtualSensor(
            sensor_id=sensor_id,
            name=meta.get("name", sensor_id),
            token=tokens[sensor_id],
            latitude=location["latitude"],
            longitude=location["longitude"],
        )
        # Continue after the last accepted reading so a restart does not resend
        # sequence numbers the backend already has.
        latest = meta.get("latest_reading") or {}
        if isinstance(latest.get("sequence_number"), int):
            sensor.sequence_number = latest["sequence_number"] + 1
        sensors[sensor_id] = sensor
        print(f"✓ {sensor_id} ready at {location['latitude']}, {location['longitude']} (next seq {sensor.sequence_number})")

    if locations_changed:
        write_json_atomic(locations_path, locations)

    return sensors


def load_sensors(tokens_file_path: str, locations_file_path: str, api_base_url: str) -> List[VirtualSensor]:
    """Load sensor tokens and locations from config files.
    
    The simulator maintains internally configured geographical locations for each sensor.
    These coordinates are included in every reading payload. This represents the expected
    behavior of physical devices that have GPS hardware or a configured location.
    
    Note: We fetch sensor names from the API for display purposes only. Coordinates come
    from the local configuration file (or are generated and saved there), not from the backend,
    unless the file has no entry and the backend already knows the device's location.
    """
    tokens_path = Path(tokens_file_path)
    if not tokens_path.exists():
        print(f"⚠ Tokens file not found yet: {tokens_file_path} (will keep checking)")
    sensors = sync_sensors({}, tokens_path, Path(locations_file_path), api_base_url)
    print(f"✓ Initialized {len(sensors)} virtual sensors\n")
    return list(sensors.values())


def run_simulation(
    sensors: List[VirtualSensor],
    api_base_url: str,
    tokens_file_path: Optional[str] = None,
    locations_file_path: Optional[str] = None,
):
    """Main simulation loop. Reloads the config files each round when paths are given."""
    print("🚀 Starting simulation loop (Ctrl+C to stop)\n")
    
    active: Dict[str, VirtualSensor] = {s.sensor_id: s for s in sensors}
    total_submissions = 0
    successful_submissions = 0
    rounds = 0
    
    try:
        while True:
            if tokens_file_path and locations_file_path:
                sync_sensors(active, Path(tokens_file_path), Path(locations_file_path), api_base_url)

            # Submit readings from all active sensors
            for sensor in list(active.values()):
                # Check if spike has expired
                sensor.check_spike_expiry()
                
                # Submit reading if active
                if sensor.active:
                    success = sensor.submit_reading(api_base_url)
                    total_submissions += 1
                    if success:
                        successful_submissions += 1
            
            # Log stats every 10 rounds
            rounds += 1
            if total_submissions > 0 and rounds % 10 == 0:
                success_rate = (successful_submissions / total_submissions) * 100
                print(f"\n📊 Stats: {successful_submissions}/{total_submissions} successful ({success_rate:.1f}%)\n")
            
            # Sleep 5-10 seconds before next round
            sleep_duration = random.uniform(5, 10)
            time.sleep(sleep_duration)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹ Simulation stopped")
        success_rate = (successful_submissions / total_submissions * 100) if total_submissions > 0 else 0
        print(f"📊 Final stats: {successful_submissions}/{total_submissions} successful ({success_rate:.1f}%)")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='Virtual sensor simulator for community air quality monitoring'
    )
    
    parser.add_argument(
        '--api-url',
        default='http://localhost:8001',
        help='Backend API base URL (default: http://localhost:8001)'
    )
    
    parser.add_argument(
        '--tokens-file',
        default='data/sensor_tokens.json',
        help='Path to sensor tokens JSON file (default: data/sensor_tokens.json)'
    )
    
    parser.add_argument(
        '--locations-file',
        default='data/sensor_locations.json',
        help='Path to sensor locations JSON file (default: data/sensor_locations.json)'
    )
    
    parser.add_argument(
        '--spike',
        metavar='SENSOR_ID',
        help='Trigger pollution spike for specified sensor'
    )
    
    parser.add_argument(
        '--disconnect',
        metavar='SENSOR_ID',
        help='Disconnect specified sensor (stop submissions)'
    )
    
    parser.add_argument(
        '--reconnect',
        metavar='SENSOR_ID',
        help='Reconnect specified sensor (resume submissions)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Duration in seconds for spike scenario (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Resolve tokens file path
    tokens_file = Path(args.tokens_file)
    if not tokens_file.is_absolute():
        # Resolve relative to backend directory
        backend_dir = Path(__file__).parent.parent.parent
        tokens_file = backend_dir / tokens_file
    
    # Resolve locations file path
    locations_file = Path(args.locations_file)
    if not locations_file.is_absolute():
        # Resolve relative to backend directory
        backend_dir = Path(__file__).parent.parent.parent
        locations_file = backend_dir / locations_file
    
    # Load sensors
    try:
        sensors = load_sensors(str(tokens_file), str(locations_file), args.api_url)
    except Exception as e:
        print(f"❌ Error loading sensors: {e}")
        return 1
    
    # Handle scenario commands
    if args.spike:
        sensor = next((s for s in sensors if s.sensor_id == args.spike), None)
        if not sensor:
            print(f"❌ Sensor {args.spike} not found")
            return 1
        sensor.trigger_spike(args.duration)
        print(f"\n💡 Spike triggered. Run simulation to see effect:")
        print(f"   python -m app.simulator.virtual_sensors --api-url {args.api_url}")
        return 0
    
    if args.disconnect:
        sensor = next((s for s in sensors if s.sensor_id == args.disconnect), None)
        if not sensor:
            print(f"❌ Sensor {args.disconnect} not found")
            return 1
        sensor.active = False
        print(f"🔌 {args.disconnect} disconnected")
        print(f"\n💡 To see effect, run simulation:")
        print(f"   python -m app.simulator.virtual_sensors --api-url {args.api_url}")
        return 0
    
    if args.reconnect:
        sensor = next((s for s in sensors if s.sensor_id == args.reconnect), None)
        if not sensor:
            print(f"❌ Sensor {args.reconnect} not found")
            return 1
        sensor.active = True
        print(f"✓ {args.reconnect} reconnected")
        print(f"\n💡 To see effect, run simulation:")
        print(f"   python -m app.simulator.virtual_sensors --api-url {args.api_url}")
        return 0
    
    # Run simulation
    run_simulation(sensors, args.api_url, str(tokens_file), str(locations_file))
    return 0


if __name__ == '__main__':
    exit(main())
