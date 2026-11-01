#!/bin/bash

echo "🔄 Restarting backend to load community sensor endpoints..."

# Stop old backend
echo "Stopping old backend process..."
sudo pkill -f "uvicorn app.main:app"
sleep 2

# Start new backend
echo "Starting backend with community sensor routes..."
cd /home/vishwas/Desktop/CC/community-air-quality/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

sleep 3

# Test if it's working
echo ""
echo "Testing community sensor endpoint..."
curl -s http://localhost:8000/api/v1/community/sensors | head -5

echo ""
echo "✅ Backend restarted! Community sensor API should be available."
echo "📍 Backend running at: http://localhost:8000"
echo "📖 API docs at: http://localhost:8000/docs"
