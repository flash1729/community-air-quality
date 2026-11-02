"""
Virtual Sensor Simulator for Community Air Quality Monitoring

Run from backend/ with venv active: 
  python -m app.simulator.virtual_sensors

Requires backend API running on --api-url. Reads tokens from --tokens-file.
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
from typing import Dict, List, Optional

import requests


class VirtualSensor:
    """Represents a virtual IoT air quality sensor."""
    
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


def load_sensors(tokens_file_path: str, api_base_url: str) -> List[VirtualSensor]:
    """Load sensor tokens and fetch metadata from API."""
    tokens_path = Path(tokens_file_path)
    
    if not tokens_path.exists():
        raise FileNotFoundError(f"Tokens file not found: {tokens_file_path}")
    
    with open(tokens_path, 'r') as f:
        tokens = json.load(f)
    
    print(f"📖 Loaded {len(tokens)} sensor tokens from {tokens_file_path}")
    
    # Fetch sensor metadata from API
    try:
        response = requests.get(f"{api_base_url}/api/v1/community/sensors", timeout=10)
        response.raise_for_status()
        sensors_data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch sensor metadata from API: {e}")
    
    # Create sensor map for quick lookup
    sensors_map = {s['id']: s for s in sensors_data}
    
    # Create VirtualSensor instances
    virtual_sensors = []
    for sensor_id, token in tokens.items():
        if sensor_id not in sensors_map:
            print(f"⚠ Warning: {sensor_id} found in tokens but not in API response")
            continue
            
        sensor_meta = sensors_map[sensor_id]
        virtual_sensor = VirtualSensor(
            sensor_id=sensor_id,
            name=sensor_meta['name'],
            token=token,
            latitude=sensor_meta['latitude'],
            longitude=sensor_meta['longitude']
        )
        virtual_sensors.append(virtual_sensor)
    
    print(f"✓ Initialized {len(virtual_sensors)} virtual sensors\n")
    return virtual_sensors


def run_simulation(sensors: List[VirtualSensor], api_base_url: str):
    """Main simulation loop."""
    print("🚀 Starting simulation loop (Ctrl+C to stop)\n")
    
    total_submissions = 0
    successful_submissions = 0
    
    try:
        while True:
            # Submit readings from all active sensors
            for sensor in sensors:
                # Check if spike has expired
                sensor.check_spike_expiry()
                
                # Submit reading if active
                if sensor.active:
                    success = sensor.submit_reading(api_base_url)
                    total_submissions += 1
                    if success:
                        successful_submissions += 1
            
            # Log stats every 10 submissions per sensor
            if total_submissions > 0 and total_submissions % (len(sensors) * 10) == 0:
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
    
    # Load sensors
    try:
        sensors = load_sensors(str(tokens_file), args.api_url)
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
    run_simulation(sensors, args.api_url)
    return 0


if __name__ == '__main__':
    exit(main())
