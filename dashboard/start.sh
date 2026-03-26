#!/bin/bash
# Silver Hawk Trading Dashboard — Start Script
# Usage: bash dashboard/start.sh

cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"

echo "Silver Hawk Trading Dashboard"
echo "=============================="

# Start backend
echo "Starting Flask API on :5050..."
cd backend
PYTHONPATH="$ROOT" python3 server.py &
BACKEND_PID=$!
cd ..

# Start frontend
echo "Starting Vite React on :5173..."
cd frontend
npm run dev -- --host 2>/dev/null &
FRONTEND_PID=$!
cd ..

echo ""
echo "  Dashboard: http://localhost:5173"
echo "  API:       http://localhost:5050"
echo ""
echo "  Press Ctrl+C to stop"

trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
