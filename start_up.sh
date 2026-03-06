#!/bin/bash

echo "🚀 Starting Echify: Bridging the Silence..."

# 1. Initialize the Virtual Camera Hardware
echo "⚙️  Setting up V4L2 Loopback..."
sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1
sudo chmod 777 /dev/video10

# 2. Start the AI Backend in the background
echo "🧠 Starting AI Backend..."
cd /home/sms/Echify-App/backend
source venv/bin/activate
# Run uvicorn in background (&)
uvicorn main:app --host 127.0.0.1 --port 8000 & 
BACKEND_PID=$!

# 3. Start the Camera Engine and UI
echo "📷 Starting Camera Engine and UI..."
cd /home/sms/Echify-App/hardware/camera
python3 camera_engine.py

# Cleanup: Kill the backend when you close the UI
kill $BACKEND_PID