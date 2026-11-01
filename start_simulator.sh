#!/bin/bash

echo "🌐 Starting Virtual Sensor Simulator..."
echo ""
echo "This will simulate 10 air quality sensors across Bengaluru"
echo "sending data to the backend API."
echo ""
echo "Commands available in simulator:"
echo "  start              - Begin sending sensor data"
echo "  spike SENSOR_001   - Trigger pollution spike in Koramangala"
echo "  disconnect SENSOR_005 - Simulate sensor failure"
echo "  reconnect SENSOR_005  - Restore sensor"
echo "  status             - Show current state"
echo "  quit               - Exit"
echo ""
echo "Press Enter to continue..."
read

cd /home/vishwas/Desktop/CC/community-air-quality/backend
python -m app.simulator.virtual_sensors
