#!/bin/bash

BASE_DIR="/home/sms/Echify-App"

echo "🧹 Step 0: Cleaning up old processes and drivers..."
# Kill anything running on your ports
sudo fuser -k 8000/tcp 2>/dev/null
sudo fuser -k 3000/tcp 2>/dev/null

# Force reload the camera driver to fix the 'not an output device' error
sudo modprobe -r v4l2loopback 2>/dev/null
sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1
sudo chmod 777 /dev/video10

echo "🚀 Starting Echify..."

# 1. Start AI Backend
echo "🧠 Starting AI Backend..."
cd "$BASE_DIR/backend"
source venv/bin/activate
# Added --reload for easier debugging during development
uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Give the backend 3 seconds to fully initialize the AI model
sleep 2

# 2. Start Camera Engine & UI
echo "📷 Starting Camera Engine and UI..."
cd "$BASE_DIR/hardware/camera"
python3 camera_engine.py

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null