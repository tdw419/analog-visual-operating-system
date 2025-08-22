#!/bin/bash

# Exit on any error
set -e

# Function to kill background jobs on exit
cleanup() {
    echo "Shutting down servers..."
    # The 'jobs -p' command lists the process IDs of all background jobs.
    # The 'kill' command sends a termination signal to these processes.
    # The '2>/dev/null' part redirects any error messages (like "no such process") to /dev/null, so they aren't displayed.
    kill $(jobs -p) 2>/dev/null
    echo "Cleanup complete."
}

# Trap the EXIT signal to run the cleanup function when the script exits.
trap cleanup EXIT

# 1. Check for MODEL_PATH
if [ -z "$MODEL_PATH" ]; then
    echo "Error: The MODEL_PATH environment variable is not set."
    echo "Please set it to the absolute path of your GGUF model file."
    exit 1
fi

echo "✅ MODEL_PATH is set to: $MODEL_PATH"

# 2. Install dependencies
echo "📦 Installing dependencies from server/requirements.txt..."
pip install -r server/requirements.txt

# 3. Start backend server
echo "🚀 Starting backend server on http://localhost:8844..."
(cd server && uvicorn server:app --host 0.0.0.0 --port 8844 > ../server.log 2>&1) &
BACKEND_PID=$!

# 4. Start frontend server
echo "🎨 Starting frontend server on http://localhost:8080..."
(cd web && python -m http.server 8080 > ../frontend.log 2>&1) &
FRONTEND_PID=$!

echo "✅ Servers are running!"
echo "   - Backend logs: server.log"
echo "   - Frontend logs: frontend.log"
echo ""
echo "👉 Open your browser and navigate to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to shut down the servers."

# Wait for the background processes to finish.
# This keeps the script alive, so the trap can catch Ctrl+C.
wait $BACKEND_PID
wait $FRONTEND_PID
