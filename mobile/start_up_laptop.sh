#!/bin/bash
# start_up_laptop.sh — for development on a laptop (no Pi hardware needed)

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "BASE_DIR resolved to: $BASE_DIR"

echo "Stopping old processes..."
pkill -f "python -m http.server 3000" 2>/dev/null
pkill -f "uvicorn src.main:app --host 0.0.0.0 --port 8000" 2>/dev/null

sleep 2

echo "Building Web UI..."
cd "$BASE_DIR/mobile" || exit 1
rm -rf "$BASE_DIR/mobile/dist"
npx expo export -p web --clear

if [ $? -ne 0 ]; then
    echo "Web build failed"
    exit 1
fi

if [ ! -f "$BASE_DIR/mobile/dist/index.html" ]; then
    echo "dist/index.html not found after build"
    exit 1
fi

echo "Web UI built successfully"

echo "Starting Web Server..."
cd "$BASE_DIR/mobile/dist" || exit 1
python -m http.server 3000 > "$BASE_DIR/web.log" 2>&1 &
SERVER_PID=$!

sleep 2

if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "Web server failed to start. Check: $BASE_DIR/web.log"
    exit 1
fi

echo "Web server running on http://localhost:3000"

echo "Starting Backend..."
cd "$BASE_DIR/backend" || exit 1
source "$BASE_DIR/venv/Scripts/activate" 2>/dev/null || source "$BASE_DIR/venv/bin/activate"
PYTHONIOENCODING=utf-8 uvicorn src.main:app --host 0.0.0.0 --port 8000 > "$BASE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 5

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start. Check: $BASE_DIR/backend.log"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "Backend running on http://localhost:8000"
echo ""
echo "All systems active. Open your browser at: http://localhost:3000"
echo "Press Ctrl+C to stop all processes."

cleanup() {
    echo "Stopping all processes..."
    kill $BACKEND_PID $SERVER_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

wait