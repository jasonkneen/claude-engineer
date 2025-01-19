#!/bin/bash

# Enable error handling
set -e

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    exit
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Check for required commands
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting." >&2; exit 1; }
command -v lsof >/dev/null 2>&1 || { echo "lsof is required but not installed. Aborting." >&2; exit 1; }

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please create it first." >&2
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate || { echo "Failed to activate virtual environment" >&2; exit 1; }

# Start WebSocket server
echo "Starting WebSocket server..."
cd visualization/memory-dashboard
node start-servers.js &
SERVER_PID=$!
cd ../..

# Wait for the server to be ready
echo "Waiting for WebSocket server to start on port 8000..."
for i in {1..30}; do
    if lsof -i:8000 >/dev/null 2>&1; then
        echo "WebSocket server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Timeout waiting for WebSocket server" >&2
        exit 1
    fi
    sleep 1
done

# Run CE3
echo "Starting CE3..."
python ce3.py

